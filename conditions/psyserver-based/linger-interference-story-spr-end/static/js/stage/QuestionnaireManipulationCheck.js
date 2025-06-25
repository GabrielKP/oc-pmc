define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  let warning_text =
    '<div class="alert alert-danger"><i>Please answer all questions!</i></div>';
  let current_page = 0;

  let continued_pages;
  let separated_pages;
  let delayed_continued;

  function _finish_task() {
    $(".collectible").each(function () {
      study.data.record_trialdata({
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
    study.next();
  }

  return {
    name: "questionnaire_manipulation_check",
    init: function (_study) {
      study = _study;

      // Pages setup
      continued_pages = new Pages();
      separated_pages = new Pages();
      delayed_continued = new Pages();

      return Promise.all([
        continued_pages.init(
          study,
          "questionnaires/manipulation_check/1_continued.html"
        ),
        separated_pages.init(
          study,
          "questionnaires/manipulation_check/1_separated.html"
        ),
        delayed_continued.init(
          study,
          "questionnaires/manipulation_check/1_delayed_continued.html"
        ),
      ]);
    },
    show: function () {
      switch (study.config["condition"]) {
        case "continued":
          continued_pages.next();
          break;

        case "separated":
          separated_pages.next();
          break;

        case "delayed-continued":
          delayed_continued.next();
          break;
      }

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
