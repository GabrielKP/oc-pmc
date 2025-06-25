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
    name: "questionnaire_transportation_interference",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        ["questionnaires/transportation_interference.html"],
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
    },
    finish_task: function () {
      _finish_task();
    },
  };
});
