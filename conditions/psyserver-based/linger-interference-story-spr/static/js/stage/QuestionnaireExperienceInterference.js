define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  let warning_text =
    '<div class="alert alert-danger"><i>Please answer all questions!</i></div>';
  let current_page = 0;

  function _finish_task(linger_rating) {
    $(".collectible").each(function () {
      study.data.record_trialdata({
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
    if ((current_page == 1) & (linger_rating != "1")) _page_2();
    else study.next();
  }

  function _page_1() {
    // functions
    function _all_selected_1() {
      if ($("select.changed").length !== $("select.collectible").length)
        return false;
      if ($("#interference_explanation").val().trim().length < 3) return false;
      return true;
    }

    // show page
    pages.next();
    current_page = 1;

    // bind conditional enable
    $(".collectible").on("change", function () {
      $(this).addClass("changed");

      if (_all_selected_1()) {
        $("#warning").html("");
        $("#submit")
          .off()
          .on("click", function () {
            _finish_task($("#linger_rating_interference").val());
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
  }

  function _page_2() {
    // check functions
    function _all_selected_2() {
      if ($("select.changed").length != $("select.collectible").length)
        return false;
      if ($("#volition_interference_explanation").val().trim().length < 3)
        return false;
      return true;
    }

    // show page
    pages.next();
    current_page = 2;

    // bind conditional enable
    $(".collectible").on("change", function () {
      $(this).addClass("changed");

      if (_all_selected_2()) {
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
  }

  return {
    name: "questionnaire_experience_interference",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "questionnaires/experience_interference/1.html",
          "questionnaires/experience_interference/2.html",
        ],
        function () {
          study.next();
        }
      );
    },
    show: function () {
      _page_1();
    },
    finish_task: function () {
      _finish_task();
    },
  };
});
