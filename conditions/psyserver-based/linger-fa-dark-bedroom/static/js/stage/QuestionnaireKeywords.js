define(["component/Pages"], function (Pages) {
  let study;
  let pages;

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

  check_selected = function () {
    let filled = true;
    $(".collectible").each(function () {
      if ($(this).val().trim().length < 2) filled = false;
    });
    return filled;
  };

  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  conditional_enable_button = function () {};

  $("#submit").on("click", function () {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please enter 10 keywords!</i></div>'
    );
  });

  return {
    name: "questionnaire_keywords",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["questionnaires/keywords.html"], function () {
        study.next();
      });
    },
    show: function () {
      pages.next();

      console.log($(".collectible"));

      // bind conditional enable
      $(".collectible").on("change", function () {
        if (check_selected()) {
          console.debug("Everything filled: enabling button");
          // $("#next").prop("disabled", false);
          // remove warning if it was there.
          $("#warning").html("");
          $("#submit")
            .off()
            .on("click", function () {
              _finish_task();
            });
        } else {
          console.debug("Something is not filled.");
          $("#submit")
            .off()
            .on("click", function () {
              $("#warning").html(
                '<div class="alert alert-danger"><i>Please enter 10 keywords!</i></div>'
              );
            });
        }
      });

      // bind submit button
      $("#submit").on("click", () => {
        $("#warning").html(
          '<div class="alert alert-danger mx-5"><i>Please enter all 10 keywords</i></div>'
        );
      });
    },
    finish_task: function () {
      _finish_task();
    },
  };
});
