/**********************
 * Demographic Survey *
 **********************/

var QuestionnaireDemographics = function () {
  // task functions
  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: "q_demographics",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
    $("conditional_text").each(function () {
      psiTurk.recordTrialData({
        phase: "q_demographics",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    $("#submit").off();
    record_responses();
    psiTurk.recordTrialData({ phase: "q_demographics", status: "end" });
    finish_questionnaire_demographics();
  };

  psiTurk.showPage("questionnaires/demographics.html");
  psiTurk.recordTrialData({ phase: "q_demographics", status: "begin" });

  // debug skip
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  check_selected = function () {
    // Checks standard fields
    if (!($("select.changed").length === $("select.qselect").length))
      return false;

    // Checks native language input, if no, require text field
    if (
      ($("#demographics_nativelang").val() == "N") &
      ($("#demographics_nativelang_text").val().trim().length == 0)
    )
      return false;

    // Same as above but fluency
    if (
      ($("#demographics_fluency").val() == "N") &
      ($("#demographics_fluency_text").val().trim().length == 0)
    )
      return false;

    // Checks the if time is there (in case user deletes it again)
    if ($("#demographics_currenttime").val().length == 0) {
      return false;
    }

    return true;
  };
  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  conditional_enable_button = function () {
    $("#submit").unbind();
    if (check_selected()) {
      console.debug("Everything filled: enabling button");
      // $("#next").prop("disabled", false);
      // remove warning if it was there.
      $("#warning").html("");
      $("#submit")
        .off()
        .on("click", function () {
          finish_task();
        });
    } else {
      console.debug("Something is not filled.");
      $("#submit").on("click", function () {
        $("#warning").html(
          '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
        );
      });
    }
  };

  $(".qselect").on("change", function () {
    // add to changed list
    $(this).addClass("changed");

    console.debug(this.id);

    // check if text field has to be displayed
    if (this.id == "demographics_nativelang") {
      if (this.value == "N") $("#demographics_nativelang_text").show();
      else $("#demographics_nativelang_text").hide();
    }
    if (this.id == "demographics_fluency") {
      if (this.value == "N") $("#demographics_fluency_text").show();
      else $("#demographics_fluency_text").hide();
    }
    conditional_enable_button();
  });

  $("input.conditional_text").on("change", function () {
    conditional_enable_button();
  });

  $("#submit").on("click", function () {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  });
};
