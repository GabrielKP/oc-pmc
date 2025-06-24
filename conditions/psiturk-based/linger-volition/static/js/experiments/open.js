/*****************
 * Comprehension *
 *****************/

var QuestionnaireOpen = function () {
  // functions for data submission to server
  var error_message =
    "<h1>Oops!</h1><p>Something went wrong submitting your study. This might happen if you lose your internet connection. Press the button to resubmit.</p><button id='resubmit'>Resubmit</button>";

  prompt_resubmit = function () {
    document.body.innerHTML = error_message;
    $("#resubmit").on("click", resubmit);
  };

  save_success = function () {
    psiTurk.completeHIT();
  };

  resubmit = function () {
    document.body.innerHTML = "<h1>Trying to resubmit...</h1>";
    reprompt = setTimeout(prompt_resubmit, 10000);

    psiTurk.saveData({
      success: save_success,
      error: prompt_resubmit,
    });
  };

  // functions to record data from questionnaire
  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: "q_open",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    $("#submit").off();
    record_responses();
    psiTurk.recordTrialData({ phase: "q_open", status: "end" });
    psiTurk.saveData({
      success: save_success,
      error: prompt_resubmit,
    });
  };

  psiTurk.showPage("questionnaires/open.html");
  psiTurk.recordTrialData({ phase: "q_open", status: "begin" });

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
      '<div class="alert alert-danger"><i>Please answer the first question!</i></div>'
    );
  });

  conditional_enable_button = function () {
    if (
      $("#content_attention").val() == "N" ||
      ($("#content_attention").val() == "Y" &&
        $("#content_attention_text").val().trim().length > 3)
    ) {
      console.debug("Q1 filled: enabling button");
      $("#warning").html("");
      $("#submit")
        .off()
        .on("click", function () {
          finish_task();
        });
    } else {
      console.debug("Something is not filled.");
      $("#submit")
        .off()
        .on("click", function () {
          $("#warning").html(
            '<div class="alert alert-danger"><i>Please answer the first question!</i></div>'
          );
        });
    }
  };

  $("#content_attention").on("change", function () {
    conditional_enable_button();
  });

  $("input.conditional_text").on("change", function () {
    conditional_enable_button();
  });

  $(".qselect").on("change", function () {
    // check if text field has to be displayed
    if (this.id == "clarity_rating") {
      let clarity_rating = parseInt(this.value);
      if (clarity_rating < 6) $("#clarity_explanation").show();
      else $("#clarity_explanation").hide();
    }
    if (this.id == "content_attention") {
      let content_attention = this.value;
      if (content_attention == "Y") $("#content_attention_text").show();
      else $("#content_attention_text").hide();
    }
  });
};
