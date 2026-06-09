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
    else if (current_page == 2) pages.next();
    else {
      console.log("Error: current_page out of range");
    }
  }

  function _page_1() {
    // show page
    pages.next();
    current_page = 1;

    // bind submit button
    $("#submit")
      .off()
      .on("click", function () {
        _finish_task();
      });
  }

  function _page_2() {
    // check functions
    function _all_selected_2() {
      return $("select.changed").length === $("select.collectible").length;
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
    $("#submit")
      .off()
      .on("click", () => {
        $("#warning").html(warning_text);
      });
  }

  return {
    name: "questionnaire_lingering_24h",
    init: function (_study) {
      study = _study;
      pages = new Pages();
      return pages.init(
        study,
        [
          "questionnaires/lingering_24h/1.html",
          "questionnaires/lingering_24h/2.html",
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
