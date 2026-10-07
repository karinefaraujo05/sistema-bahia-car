// Guia que acompanha o usuário pelas telas de verdade.
// Começa na Central de ajuda ("Fazer agora"), guarda o passo no sessionStorage
// e, em cada tela do fluxo, mostra uma barra no topo e destaca o botão certo.
(function () {
  "use strict";

  var TOURS = {
    venda: {
      titulo: "Vender um carro da loja",
      passos: [
        { match: "/passo/quem/", foco: "form button.botao-primario", texto: "Escolha <b>quem está comprando</b> — busque o cliente ou cadastre um novo — e toque em <b>Continuar</b> (botão destacado)." },
        { match: "/passo/carro/", foco: "form button.botao-primario", texto: "Escolha <b>qual carro</b> está saindo do estoque e toque em <b>Continuar</b>." },
        { match: "/passo/pagamento/", foco: "form button.botao-primario", texto: "Preencha <b>os valores e a forma de pagamento</b> e toque em <b>Continuar</b>." },
        { match: "/revisao/", foco: "form button.botao-primario", texto: "Confira tudo e toque em <b>Confirmar</b>. Pronto, venda registrada! 🎉", fim: true }
      ]
    },
    compra: {
      titulo: "Comprar um carro pra loja",
      passos: [
        { match: "/passo/quem/", foco: "form button.botao-primario", texto: "Diga <b>de quem você comprou</b> — busque ou cadastre o vendedor — e toque em <b>Continuar</b>." },
        { match: "/passo/carro/", foco: "form button.botao-primario", texto: "Cadastre o <b>carro que entrou</b> e toque em <b>Continuar</b>." },
        { match: "/passo/pagamento/", foco: "form button.botao-primario", texto: "Diga <b>quanto você pagou</b> e a forma de pagamento, e toque em <b>Continuar</b>." },
        { match: "/revisao/", foco: "form button.botao-primario", texto: "Confira e toque em <b>Confirmar</b>. O carro entrou no estoque! 🎉", fim: true }
      ]
    },
    troca: {
      titulo: "Fazer uma troca",
      passos: [
        { match: "/passo/quem/", foco: "form button.botao-primario", texto: "Diga <b>quem é o cliente</b> da troca e toque em <b>Continuar</b>." },
        { match: "/troca/carro-loja/", foco: "form button.botao-primario", texto: "Escolha <b>o carro da loja</b> que o cliente levou e toque em <b>Continuar</b>." },
        { match: "/troca/carro-cliente/", foco: "form button.botao-primario", texto: "Cadastre <b>o carro que o cliente deu</b> na troca e toque em <b>Continuar</b>." },
        { match: "/troca/valores/", foco: "form button.botao-primario", texto: "Ajuste <b>os valores</b> (quem paga a diferença) e toque em <b>Continuar</b>." },
        { match: "/revisao/", foco: "form button.botao-primario", texto: "Confira e toque em <b>Confirmar</b>. Troca registrada! 🎉", fim: true }
      ]
    },
    consignado: {
      titulo: "Registrar um carro consignado",
      passos: [
        { match: "/consignacoes/nova/", foco: "form button.botao-primario", texto: "Cadastre o <b>dono</b> e o <b>carro</b>, defina o <b>valor mínimo</b> e a sua <b>comissão</b>, e toque em <b>Salvar</b>. O carro entra no estoque como consignado. 🎉", fim: true }
      ]
    },
    carro: {
      titulo: "Cadastrar um carro",
      passos: [
        { match: "/carros/novo/", foco: "form button.botao-primario", texto: "Preencha os dados do carro (placa, marca, modelo…), adicione <b>fotos</b> e toque em <b>Salvar</b>. 🎉", fim: true }
      ]
    },
    cliente: {
      titulo: "Cadastrar um cliente",
      passos: [
        { match: "/pessoas/nova/", foco: "form button.botao-primario", texto: "Digite o <b>CEP</b> (o endereço aparece sozinho), preencha o resto e toque em <b>Salvar</b>. 🎉", fim: true }
      ]
    }
  };

  function iniciar() {
    var id = sessionStorage.getItem("guia_tour");
    if (!id) return;
    var tour = TOURS[id];
    if (!tour) {
      sessionStorage.removeItem("guia_tour");
      return;
    }

    var caminho = window.location.pathname;
    var idx = -1;
    for (var i = 0; i < tour.passos.length; i++) {
      if (caminho.indexOf(tour.passos[i].match) !== -1) {
        idx = i;
        break;
      }
    }
    if (idx === -1) return; // Saiu do fluxo: não mostra nada, mas guarda o estado.

    var main = document.querySelector("main");
    if (!main) return;
    var passo = tour.passos[idx];
    var total = tour.passos.length;

    // Barra do guia, fixa no topo do conteúdo.
    var bar = document.createElement("div");
    bar.className = "guia-bar";
    bar.setAttribute("role", "status");

    var etapa = total > 1 ? "Passo " + (idx + 1) + " de " + total + " · " + tour.titulo : tour.titulo;

    bar.innerHTML =
      '<span class="guia-bar-icone">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>' +
      "</span>" +
      '<div class="guia-bar-texto">' +
      '<span class="guia-bar-passo">' + etapa + "</span>" +
      '<span class="guia-bar-instrucao">' + passo.texto + "</span>" +
      "</div>" +
      '<button type="button" class="guia-bar-sair" aria-label="Sair do guia">Sair</button>';

    main.insertBefore(bar, main.firstChild);

    // Destaca o botão certo da tela.
    var alvo = passo.foco ? document.querySelector(passo.foco) : null;
    if (alvo) alvo.classList.add("guia-foco");

    function sair() {
      sessionStorage.removeItem("guia_tour");
      if (alvo) alvo.classList.remove("guia-foco");
      bar.remove();
    }
    bar.querySelector(".guia-bar-sair").addEventListener("click", sair);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
