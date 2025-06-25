define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  let warning_text =
    '<div class="alert alert-danger"><i>Please answer all questions!</i></div>';

  function _finish_task() {
    $(".collectible").each(function () {
      study.data.record_trialdata({
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
    pages.next();
  }

  return {
    name: "questionnaire_transportation",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        ["questionnaires/transportation.html"],
        function () {
          study.next();
        }
      );
    },
    show: function () {
      pages.next();

      // bind conditional enable
      $(".collectible").on("change", function () {
        // add changed class for tracking
        $(this).addClass("changed");

        // check for all changed
        if ($("select.changed").length === $("select.collectible").length) {
          $("#warning").html("");
          $("#submit")
            .off()
            .on("click", function () {
              _finish_task();
            });
        } else {
          $("#submit")
            .off()
            .on("click", function () {
              $("#warning").html(warning_text);
            });
        }
      });

      // bind submit button
      $("#submit").on("click", () => {
        $("#warning").html(warning_text);
      });

      setTimeout(function () {
        if (
          $("#tran_Q0").val() == "1" ||
          $("#tran_Q0").val() == "2" ||
          $("#tran_Q0").val() == "3" ||
          $("#tran_Q0").val() == "4" ||
          $("#tran_Q0").val() == "5" ||
          $("#tran_Q0").val() == "6" ||
          $("#tran_Q0").val() == "7"
        ) {
          console.log("Redirect: " + $("#tran_Q0").val());
          window.location.href =
            "https://app.prolific.com/submissions/complete?cc=" +
            study.config["code_honeypot"];
        } else {
          console.log("All good!");
          $("#tran_Q0").removeClass("collectible");
        }
      }, 3000);
    },
    finish_task: function () {
      _finish_task();
    },
  };
});
