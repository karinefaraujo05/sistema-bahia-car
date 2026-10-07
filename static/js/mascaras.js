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

  // Ordem importa: cpf_cnpj antes de cnpj/cpf.
  var REGRAS = [
    { re: /cpf_cnpj/i, fmt: cpfCnpj, numero: true },
    { re: /cnpj/i, fmt: cnpj, numero: true },
    { re: /(^|_)cpf/i, fmt: cpf, numero: true },
    { re: /telefone|celular|whatsapp|fone/i, fmt: telefone, numero: true },
    { re: /cep/i, fmt: cep, numero: true },
    { re: /placa/i, fmt: placa, numero: false },
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
    function formatar() {
      var novo = regra.fmt(el.value);
      if (novo !== el.value) el.value = novo;
    }
    el.addEventListener("input", formatar);
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
