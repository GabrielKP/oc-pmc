define(["component/Pages"], function (Pages) {
  let study;
  let pages;
  let warning_text =
    '<div class="alert alert-danger"><i>Please answer all questions!</i></div>';
  let current_page = 0;

  function _finish_task() {
    $(".collectible").each(function () {
      study.data.record_trialdata({
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
    if (current_page == 1) _page_2();
    else if (current_page == 2) {
      // conditional on linger rating
      if ($("#linger_rating").val() == "1") study.next();
      else _page_3();
    } else if (current_page == 3) _page_4();
    else if (current_page == 4) pages.next();
    else {
      console.log("Error: current_page out of range");
    }
  }

  function _page_1() {
    // functions
    function _all_selected_1() {
      if ($("select.changed").length !== $("select.collectible").length)
        return false;
      if (
        $("#wcg_strategy").val().trim().length < 3 ||
        $("#guess_experiment").val().trim().length < 3 ||
        $("#tom_explanation").val().trim().length < 3
      )
        return false;
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

  function _page_2() {
    // check functions
    function _all_selected_2() {
      if ($("select.changed").length !== $("select.collectible").length)
        return false;
      if ($("#wcg_diff_general").val().trim().length < 3) return false;
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

  function _page_3() {
    // check functions
    function _all_selected_3() {
      if ($("select.changed").length !== $("select.collectible").length)
        return false;
      if ($("#volition_explanation").val().trim().length < 3) return false;
      return true;
    }

    // show page
    pages.next();
    current_page = 3;

    // bind conditional enable
    $(".collectible").on("change", function () {
      $(this).addClass("changed");

      if (_all_selected_3()) {
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

  function _page_4() {
    // check functions
    function _all_selected_4() {
      if ($("select.changed").length !== $("select.collectible").length)
        return false;
      if ($("#wcg_diff_explanation").val().trim().length < 3) return false;
      return true;
    }

    // show page
    pages.next();
    current_page = 4;

    // bind conditional enable
    $(".collectible").on("change", function () {
      $(this).addClass("changed");

      if (_all_selected_4()) {
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
    name: "questionnaire_experience",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "questionnaires/experience/1.html",
          "questionnaires/experience/2.html",
          "questionnaires/experience/3.html",
          "questionnaires/experience/4.html",
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
