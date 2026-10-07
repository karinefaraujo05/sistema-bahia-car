"""
Popula a empresa de DEMONSTRAÇÃO com uma loja fake completa e bonita:
carros, pessoas, vendas, troca e consignação. Também cria o usuário admin/12345.

Uso: python manage.py seed_demo
É idempotente: limpa os dados da empresa demo e recria do zero.
"""

import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection, transaction

from contas.models import Empresa, Usuario
from contratos.models import ConfiguracaoLoja, Contrato, Documento
from core.tenancy import limpar_empresa_atual, set_empresa_atual
from negocios import services
from negocios.models import (
    ComissaoTipo,
    ItemNegocio,
    Modalidade,
    Negocio,
    ParteNegocio,
    StatusNegocio,
    TipoNegocio,
)
from pessoas.models import Pessoa, TipoPessoa
from veiculos.models import Cambio, Combustivel, FotoVeiculo, Situacao, StatusVeiculo, Veiculo

HOJE = datetime.date.today()


def _mes_atras(n):
    ano, mes = HOJE.year, HOJE.month - n
    while mes <= 0:
        mes += 12
        ano -= 1
    dia = min(HOJE.day, 28)
    return datetime.date(ano, mes, dia)


class Command(BaseCommand):
    help = "Cria/recria a empresa de demonstração com dados completos e o usuário admin/12345."

    @transaction.atomic
    def handle(self, *args, **options):
        empresa, _ = Empresa.objects.get_or_create(nome="Loja Demonstração")
        set_empresa_atual(empresa)
        try:
            self._limpar(empresa)
            self._resetar_sequencias()
            self._admin(empresa)
            self._config()
            pessoas = self._pessoas()
            self._estoque_e_vendas(pessoas)
            self._troca(pessoas)
            self._consignacao(pessoas)
        finally:
            limpar_empresa_atual()
        self.stdout.write(self.style.SUCCESS("Demo criada. Entre com admin / 12345."))

    def _limpar(self, empresa):
        for modelo in (Documento, Contrato, ItemNegocio, ParteNegocio, Negocio, FotoVeiculo):
            modelo.todos.filter(empresa=empresa).delete()
        from negocios.models import Consignacao

        Consignacao.todos.filter(empresa=empresa).delete()
        Veiculo.todos.filter(empresa=empresa).delete()
        Pessoa.todos.filter(empresa=empresa).delete()
        ConfiguracaoLoja.todos.filter(empresa=empresa).delete()

    def _resetar_sequencias(self):
        from negocios.models import Consignacao

        modelos = [
            ConfiguracaoLoja, Contrato, Documento, Negocio, ItemNegocio,
            ParteNegocio, Consignacao, Veiculo, FotoVeiculo, Pessoa,
        ]
        sql = connection.ops.sequence_reset_sql(no_style(), modelos)
        with connection.cursor() as cursor:
            for comando in sql:
                cursor.execute(comando)

    def _admin(self, empresa):
        # Admin da DEMO: administrador da aplicação, mas NÃO superusuário
        # (não acessa o painel do Django, então não vê dados de outra empresa).
        admin, _ = Usuario.objects.get_or_create(
            username="admin",
            defaults={"papel": Usuario.Papel.ADMINISTRADOR},
        )
        admin.is_staff = False
        admin.is_superuser = False
        admin.papel = Usuario.Papel.ADMINISTRADOR
        admin.empresa = empresa
        admin.first_name = "Administrador"
        admin.set_password("12345")
        admin.save()

    def _config(self):
        loja = ConfiguracaoLoja.carregar()
        loja.razao_social = "Loja Demonstração Veículos Ltda"
        loja.nome_fantasia = "Loja Demonstração"
        loja.cnpj = "11222333000181"
        loja.endereco = "Av. das Palmeiras, 1000"
        loja.cidade = "São Paulo"
        loja.uf = "SP"
        loja.cep = "01001000"
        loja.representante_nome = "Ricardo Demonstração"
        loja.representante_cpf = "11144477735"
        loja.multa_percentual = Decimal("10")
        loja.save()

    def _pessoas(self):
        dados = [
            ("Ana Beatriz Martins", "52998224725", "professora", "solteira", "Rua das Flores, 120"),
            ("Bruno Carvalho Lima", "11144477735", "engenheiro", "casado", "Av. Brasil, 450"),
            ("Camila Souza Reis", "20944455566", "médica", "solteira", "Rua Ipê, 78"),
            ("Diego Alves Pinto", "30944455500", "autônomo", "casado", "Rua das Acácias, 23"),
            ("Eduarda Nunes Faria", "40944455511", "advogada", "divorciada", "Av. Central, 900"),
            ("Fábio Ramos Teixeira", "50944455522", "comerciante", "casado", "Rua do Sol, 55"),
        ]
        pessoas = {}
        for nome, cpf, prof, ec, end in dados:
            p = Pessoa.objetos.create(
                nome=nome,
                tipo=TipoPessoa.FISICA,
                cpf_cnpj=cpf,
                telefone="11988887777",
                nacionalidade="brasileira",
                estado_civil=ec,
                profissao=prof,
                rg="123456789",
                rg_orgao_emissor="SSP/SP",
                endereco=end,
                cidade="São Paulo",
                uf="SP",
                cep="01002000",
            )
            pessoas[nome.split()[0]] = p
        return pessoas

    def _carro(self, placa, marca, modelo, ano, cor, km, chassi, renavam, cambio, compra, **kw):
        return Veiculo.objetos.create(
            placa=placa,
            marca=marca,
            modelo=modelo,
            ano_fabricacao=ano,
            ano_modelo=ano + 1,
            cor=cor,
            km=km,
            combustivel=Combustivel.FLEX,
            cambio=cambio,
            chassi=chassi,
            renavam=renavam,
            tem_chave_reserva=True,
            avarias_declaradas="Nenhuma avaria aparente",
            valor_compra=Decimal(compra),
            **kw,
        )

    def _estoque_e_vendas(self, pessoas):
        # Carros que ficam no estoque (à venda).
        self._carro("RST1A23", "Jeep", "Renegade Sport 1.8", 2021, "Branco", 38000,
                    "9BGKL48U0KG100001", "10000000001", Cambio.AUTOMATICO, "92000",
                    valor_anunciado=Decimal("104900"))
        self._carro("RST2B34", "Hyundai", "HB20 Comfort 1.0", 2022, "Prata", 21000,
                    "9BGKL48U0KG100002", "10000000002", Cambio.MANUAL, "58000",
                    valor_anunciado=Decimal("72900"))
        self._carro("RST3C45", "Chevrolet", "Onix LT 1.0", 2020, "Cinza", 49000,
                    "9BGKL48U0KG100003", "10000000003", Cambio.MANUAL, "54000",
                    valor_anunciado=Decimal("66900"))
        self._carro("RST4D56", "Toyota", "Corolla XEI 2.0", 2021, "Preto", 33000,
                    "9BGKL48U0KG100004", "10000000004", Cambio.AUTOMATICO, "115000",
                    valor_anunciado=Decimal("132900"))

        # Carros vendidos (geram vendas, lucro e histórico nos últimos meses).
        vendas = [
            ("VND1A11", "Volkswagen", "Nivus Highline 1.0", 2022, "Vermelho", 28000,
             "9BGKL48U0KG200001", "20000000001", Cambio.AUTOMATICO, "98000", "118900", "Ana", 0),
            ("VND2B22", "Fiat", "Pulse Drive 1.3", 2022, "Branco", 24000,
             "9BGKL48U0KG200002", "20000000002", Cambio.AUTOMATICO, "82000", "99900", "Bruno", 1),
            ("VND3C33", "Honda", "City EXL 1.5", 2020, "Prata", 52000,
             "9BGKL48U0KG200003", "20000000003", Cambio.AUTOMATICO, "76000", "92900", "Camila", 2),
            ("VND4D44", "Renault", "Kwid Zen 1.0", 2021, "Azul", 40000,
             "9BGKL48U0KG200004", "20000000004", Cambio.MANUAL, "44000", "56900", "Diego", 3),
        ]
        for placa, marca, modelo, ano, cor, km, chassi, renavam, cambio, compra, venda, quem, mes in vendas:
            carro = self._carro(placa, marca, modelo, ano, cor, km, chassi, renavam, cambio, compra,
                                 valor_anunciado=Decimal(venda))
            negocio = Negocio.objetos.create(
                tipo=TipoNegocio.VENDA, modalidade=Modalidade.PROPRIA,
                status=StatusNegocio.RASCUNHO, data=_mes_atras(mes),
                forma_pagamento="a_vista", detalhes_pagamento="via PIX, na entrega",
            )
            ItemNegocio.objetos.create(
                negocio=negocio, veiculo=carro, valor=Decimal(venda),
                para_pessoa=pessoas[quem], km_entrega=km,
            )
            services.concluir_negocio(negocio)

    def _troca(self, pessoas):
        da_loja = self._carro("TRC1A10", "Nissan", "Kicks SV 1.6", 2021, "Laranja", 41000,
                              "9BGKL48U0KG300001", "30000000001", Cambio.AUTOMATICO, "88000",
                              valor_anunciado=Decimal("104000"))
        do_cliente = self._carro("TRC2B20", "Ford", "Ka SE 1.0", 2018, "Branco", 72000,
                                 "9BGKL48U0KG300002", "30000000002", Cambio.MANUAL, "0",
                                 situacao=Situacao.TERCEIRO)
        negocio = Negocio.objetos.create(
            tipo=TipoNegocio.TROCA, modalidade=Modalidade.PROPRIA,
            status=StatusNegocio.RASCUNHO, data=_mes_atras(0),
        )
        ItemNegocio.objetos.create(negocio=negocio, veiculo=da_loja, valor=Decimal("104000"),
                                   para_pessoa=pessoas["Eduarda"], km_entrega=41000)
        ItemNegocio.objetos.create(negocio=negocio, veiculo=do_cliente, valor=Decimal("45000"),
                                   de_pessoa=pessoas["Eduarda"], km_entrega=72000)
        services.concluir_negocio(negocio)

    def _consignacao(self, pessoas):
        carro = self._carro("CNS1A10", "Volkswagen", "T-Cross 200 TSI", 2021, "Cinza", 36000,
                            "9BGKL48U0KG400001", "40000000001", Cambio.AUTOMATICO, "0",
                            situacao=Situacao.CONSIGNADO, valor_anunciado=Decimal("119000"))
        services.criar_consignacao(
            veiculo=carro,
            proprietario=pessoas["Fábio"],
            valor_liquido_minimo=Decimal("110000"),
            comissao_tipo=ComissaoTipo.PERCENTUAL,
            comissao_valor=Decimal("5"),
            documentos_entregues="CRLV-e e chave reserva",
        )
