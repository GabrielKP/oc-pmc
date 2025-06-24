/*****************
 * Comprehension *
 *****************/

var QuestionnaireComprehension = function () {
  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: "q_comprehension",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    $("#submit").off();
    record_responses();
    psiTurk.recordTrialData({ phase: "q_comprehension", status: "end" });
    finish_questionnaire_comprehension();
  };

  psiTurk.showPage("questionnaires/comprehension.html");
  psiTurk.recordTrialData({ phase: "q_comprehension", status: "begin" });

  // debug skip
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  function show_warning() {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  }

  $("#submit").on("click", function () {
    show_warning();
  });

  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  $(".qelement").on("change", function () {
    $(this).addClass("changed");
    if ($("select.changed").length === $("select.qselect").length) {
      console.debug("All selected: enabling button");
      // $("#next").prop("disabled", false);
      // remove warning if it was there.
      $("#warning").html("");
      $("#submit")
        .off()
        .on("click", function () {
          finish_task();
        });
      button_enabled = true;
    } else {
      console.debug("One or more not selected yet!!");
    }
  });
};
