define(["component/Pages"], function (Pages) {
  let wd1 = "<div class='alert alert-danger'><b>";
  let wd2 = "</b></div>";
  let warning_text1 = "Error-code: ";
  let warning_text2 =
    "<br>Please retry. If error persists, notifiy us on prolific.";

  // captcha success
  function success_callback(h_captcha_response) {
    console.debug("captcha-success!");
    this.study.data.record_trialdata({
      status: "ongoing",
      question: "h_captcha_response",
      answer: h_captcha_response,
    });
    this.study.data.h_captcha_response = h_captcha_response;
    // bind submit button
    $("#submit").on("click", () => {
      this.study.next();
    });
    $("#submit").prop("disabled", false);
  }

  // captcha error
  function error_callback(error_code) {
    console.debug("captcha-error: ", error_code);
    $("#warning").html(wd1 + warning_text1 + error_code + warning_text2 + wd2);
    this.study.data.record_trialdata({
      status: "ongoing",
      question: "h_captcha_error",
      answer: error_code,
    });
    hcaptcha.reset();
  }

  function show_hcaptcha() {
    hcaptcha.render("captcha-div", {
      sitekey: "bfb2a55a-b784-4e44-b02e-33dce01203f0",
      callback: success_callback,
      "error-callback": error_callback,
    });
    $("#loading-txt").text("");
  }

  function loadError(oError) {
    throw new URIError(
      `The script ${oError.target.src} didn't load correctly.`
    );
  }

  // MDN: https://developer.mozilla.org/en-US/docs/Web/API/HTMLScriptElement#dynamically_importing_scripts
  function affixScriptToHead(url, onloadFunction) {
    const newScript = document.createElement("script");
    newScript.onerror = loadError;
    if (onloadFunction) {
      newScript.onload = onloadFunction;
    }
    document.head.appendChild(newScript);
    newScript.src = url;
  }

  return {
    study: null,
    pages: null,
    name: "captcha",
    init: function (_study) {
      this.study = _study;
      this.pages = new Pages();
      return this.pages.init(this.study, ["captcha.html"], function () {
        this.study.next();
      });
    },
    show: function () {
      // show the form
      this.pages.next();

      window.gl_show_hcaptcha = show_hcaptcha;
      success_callback = success_callback.bind(this);

      // load hcaptcha script
      affixScriptToHead(
        "https://js.hcaptcha.com/1/api.js?onload=gl_show_hcaptcha&render=explicit",
        () => {
          console.log("hcaptcha loaded");
        }
      );
    },
  };
});
