// Máscaras que formatam enquanto o usuário digita (CPF, CNPJ, telefone, CEP, placa).
// Aplica sozinho em qualquer campo cujo nome/id combine, em todas as telas.
// No envio do formulário, os campos de número voltam a só dígitos, pra o servidor
// receber limpo (os modelos já guardam só dígitos).
(function () {
  "use strict";

  function dig(v) {
    return (v || "").replace(/\D/g, "");
  }

  function cpf(v) {
    return dig(v)
      .slice(0, 11)
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }

  function cnpj(v) {
    return dig(v)
      .slice(0, 14)
      .replace(/^(\d{2})(\d)/, "$1.$2")
      .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/\.(\d{3})(\d)/, ".$1/$2")
      .replace(/(\d{4})(\d)/, "$1-$2");
  }

  function cpfCnpj(v) {
    return dig(v).length <= 11 ? cpf(v) : cnpj(v);
  }

  function cep(v) {
    return dig(v).slice(0, 8).replace(/(\d{5})(\d)/, "$1-$2");
  }

  function telefone(v) {
    v = dig(v).slice(0, 11);
    if (v.length <= 10) {
      return v.replace(/(\d{2})(\d)/, "($1) $2").replace(/(\d{4})(\d)/, "$1-$2");
    }
    return v.replace(/(\d{2})(\d)/, "($1) $2").replace(/(\d{5})(\d)/, "$1-$2");
  }

  function placa(v) {
    return (v || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7);
  }

  // --- Validação (alerta de erro) ---
  function iguais(c) {
    return /^(\d)\1+$/.test(c);
  }
  function cpfValido(c) {
    c = dig(c);
    if (c.length !== 11 || iguais(c)) return false;
    var s = 0, i, d;
    for (i = 0; i < 9; i++) s += +c[i] * (10 - i);
    d = 11 - (s % 11); if (d >= 10) d = 0;
    if (d !== +c[9]) return false;
    s = 0;
    for (i = 0; i < 10; i++) s += +c[i] * (11 - i);
    d = 11 - (s % 11); if (d >= 10) d = 0;
    return d === +c[10];
  }
  function cnpjValido(c) {
    c = dig(c);
    if (c.length !== 14 || iguais(c)) return false;
    function calc(base) {
      var tam = base.length, soma = 0, pos = tam - 7, i;
      for (i = 0; i < tam; i++) { soma += +base[i] * pos--; if (pos < 2) pos = 9; }
      var r = soma % 11;
      return r < 2 ? 0 : 11 - r;
    }
    if (calc(c.slice(0, 12)) !== +c[12]) return false;
    return calc(c.slice(0, 13)) === +c[13];
  }
  function vCpf(v) { var d = dig(v); return !d || cpfValido(d) ? "" : "CPF inválido."; }
  function vCnpj(v) { var d = dig(v); return !d || cnpjValido(d) ? "" : "CNPJ inválido."; }
  function vCpfCnpj(v) { var d = dig(v); return !d ? "" : (d.length <= 11 ? vCpf(v) : vCnpj(v)); }
  function vTelefone(v) { var d = dig(v); return !d || (d.length >= 10 && d.length <= 11) ? "" : "Telefone incompleto."; }
  function vCep(v) { var d = dig(v); return !d || d.length === 8 ? "" : "CEP incompleto."; }
  function vPlaca(v) { var p = placa(v); return !p || p.length === 7 ? "" : "Placa incompleta."; }

  // Ordem importa: cpf_cnpj antes de cnpj/cpf.
  var REGRAS = [
    { re: /cpf_cnpj/i, fmt: cpfCnpj, numero: true, valida: vCpfCnpj },
    { re: /cnpj/i, fmt: cnpj, numero: true, valida: vCnpj },
    { re: /(^|_)cpf/i, fmt: cpf, numero: true, valida: vCpf },
    { re: /telefone|celular|whatsapp|fone/i, fmt: telefone, numero: true, valida: vTelefone },
    { re: /cep/i, fmt: cep, numero: true, valida: vCep },
    { re: /placa/i, fmt: placa, numero: false, valida: vPlaca },
  ];

  function regraDe(el) {
    var chave = (el.name || "") + " " + (el.id || "");
    for (var i = 0; i < REGRAS.length; i++) {
      if (REGRAS[i].re.test(chave)) return REGRAS[i];
    }
    return null;
  }

  function aplicar(el) {
    if (el.dataset.mascaraOn) return;
    var regra = regraDe(el);
    if (!regra) return;
    el.dataset.mascaraOn = "1";
    if (regra.numero) {
      el.dataset.mascaraNum = "1";
      el.setAttribute("inputmode", el.getAttribute("inputmode") || "numeric");
    }
    // O valor formatado é maior que o limite de dígitos; tira o maxlength.
    el.removeAttribute("maxlength");
    var erroEl = null;
    function mostrarErro(msg) {
      if (!erroEl) {
        if (!msg) return;
        erroEl = document.createElement("p");
        erroEl.className = "mascara-erro mt-1 text-sm text-vermelho";
        el.insertAdjacentElement("afterend", erroEl);
      }
      erroEl.textContent = msg || "";
      erroEl.style.display = msg ? "" : "none";
      el.classList.toggle("campo-erro", !!msg);
    }
    function formatar() {
      var novo = regra.fmt(el.value);
      if (novo !== el.value) el.value = novo;
      // Enquanto digita, só tira o erro quando corrige (não enche o saco antes).
      if (erroEl && erroEl.textContent && regra.valida) mostrarErro(regra.valida(el.value));
    }
    el.addEventListener("input", formatar);
    el.addEventListener("blur", function () {
      if (regra.valida) mostrarErro(regra.valida(el.value));
    });
    if (el.value) formatar();
  }

  function varrer(raiz) {
    var campos = (raiz || document).querySelectorAll(
      "input[type=text], input[type=search], input[type=tel], input:not([type])"
    );
    Array.prototype.forEach.call(campos, aplicar);
  }

  // Ao enviar um formulário de verdade, limpa os campos de número pra só dígitos.
  // Pula formulários AJAX (que chamam preventDefault, como a consulta).
  document.addEventListener("submit", function (e) {
    if (e.defaultPrevented) return;
    var nums = e.target.querySelectorAll('input[data-mascara-num="1"]');
    Array.prototype.forEach.call(nums, function (el) {
      el.value = dig(el.value);
    });
  });

  document.addEventListener("DOMContentLoaded", function () {
    varrer(document);
  });
  document.addEventListener("htmx:afterSwap", function (e) {
    varrer(e.target);
  });
})();
