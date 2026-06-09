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

  function all_selected() {
    if ($("select.changed").length !== $("select.collectible").length)
      return false;

    // Checks native language input, if no, require text field
    if (
      ($("#demographics_nativelang").val() == "N") &
      ($("#demographics_nativelang_text").val().trim().length < 3)
    )
      return false;

    // Same as above but fluency
    if (
      ($("#demographics_fluency").val() == "N") &
      ($("#demographics_fluency_text").val().trim().length < 3)
    )
      return false;

    // Checks the if time is there (in case user deletes it again)
    if ($("#demographics_currenttime").val().length == 0) {
      return false;
    }

    return true;
  }

  return {
    name: "questionnaire_demographics",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        ["questionnaires/demographics.html"],
        function () {
          study.next();
        }
      );
    },
    show: function () {
      pages.next();
      // bind conditional nativelang follow up
      $("#demographics_nativelang").on("change", () => {
        if ($("#demographics_nativelang").val() == "N") {
          $("#demographics_nativelang_text").show();
        } else {
          $("#demographics_nativelang_text").hide();
        }
      });

      // bind conditional fluency follow up
      $("#demographics_fluency").on("change", () => {
        if ($("#demographics_fluency").val() == "N") {
          $("#demographics_fluency_text").show();
        } else {
          $("#demographics_fluency_text").hide();
        }
      });

      // bind conditional enable
      $(".collectible").on("change", function () {
        // add changed class for tracking
        $(this).addClass("changed");

        // check for all changed
        if (all_selected()) {
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
