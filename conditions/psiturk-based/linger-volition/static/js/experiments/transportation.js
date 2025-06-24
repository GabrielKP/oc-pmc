/******************
 * Transportation *
 ******************/

var QuestionnaireTransportation = function () {
  function record_responses() {
    $("select.qselect").each(function () {
      psiTurk.recordTrialData({
        phase: "q_transportation",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    $("#submit").off();
    record_responses();
    psiTurk.recordTrialData({ phase: "q_transportation", status: "end" });
    finish_questionnaire_transportation();
  };

  psiTurk.showPage("questionnaires/transportation.html");
  psiTurk.recordTrialData({ phase: "q_transportation", status: "begin" });

  // debug skip
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  $("#submit").on("click", function () {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  });

  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  $("select.qselect").on("change", function () {
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
    } else {
      console.debug("One or more not selected yet!!");
    }
  });
};
