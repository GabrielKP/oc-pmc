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

  conditional_enable_button = function () {
    if (
      $("#content_attention").val() == "N" ||
      ($("#content_attention").val() == "Y" &&
        $("#content_attention_text").val().trim().length > 3)
    ) {
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
          $("#warning").html(
            '<div class="alert alert-danger"><i>Please answer the first question!</i></div>'
          );
        });
    }
  };

  return {
    name: "questionnaire_open",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(study, ["questionnaires/open.html"], function () {
        study.next();
      });
    },
    show: function () {
      pages.next();
      // bind conditional clarity follow up
      $("#clarity_rating").on("change", () => {
        if ($("#clarity_rating").val() < 6) {
          $("#clarity_follow_up").show();
        } else {
          $("#clarity_follow_up").hide();
        }
      });
      // bind conditional content_attention follow up
      $("#content_attention").on("change", () => {
        if ($("#content_attention").val() == "Y") {
          $("#content_attention_follow_up").show();
        } else {
          $("#content_attention_follow_up").hide();
        }
      });
      // bind conditional enable
      $("#content_attention").on("change", conditional_enable_button);
      $("#content_attention_text").on("change", conditional_enable_button);

      // bind submit button
      $("#submit").on("click", () => {
        $("#warning").html(
          '<div class="alert alert-danger mx-5"><i>Please answer the first question!</i></div>'
        );
      });
    },
    finish_task: function () {
      _finish_task();
    },
  };
});
