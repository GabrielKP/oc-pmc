/******************************
 * Multi-step Experience Code *
 ******************************/

var QuestionnaireExperience1 = function () {
  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: "q_experience1",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    record_responses();
    psiTurk.recordTrialData({ phase: "q_experience1", status: "end" });
    currentview = new QuestionnaireExperience2();
  };

  psiTurk.showPage("questionnaires/experience1.html");
  psiTurk.recordTrialData({ phase: "q_experience1", status: "begin" });

  // debug skip
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  // Define function to prevent copy, paste, and cut
  // ref: https://jsfiddle.net/lesson8/ZxKdp/
  $("input,textarea").bind("cut copy paste", function (e) {
    e.preventDefault(); //disable cut,copy,paste
  });

  function show_warning() {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  }

  $("#submit").on("click", function () {
    show_warning();
  });

  check_selected = function () {
    // standard fields
    if (!($("select.changed").length === $("select.qselect").length)) {
      return false;
    }

    // Textbox counts if more than 2 characters are written
    if (
      $("#wcg_strategy").val().trim().length < 3 ||
      $("#guess_experiment").val().trim().length < 3
    ) {
      return false;
    }
    // check for suppress questions
    if (
      exp_condition == "button_press_suppress" ||
      exp_condition == "suppress"
    ) {
      if (
        $("#guess_suppress_1").val().trim().length < 3 ||
        $("#guess_suppress_2").val().trim().length < 3
      ) {
        return false;
      }
    }

    return true;
  };

  // show suppression questions
  if (exp_condition == "button_press_suppress" || exp_condition == "suppress") {
    $(".suppress").show();
  }

  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  $(".qelement").on("change", function () {
    if ($(this).prop("nodeName").toLowerCase() == "select") {
      $(this).addClass("changed");
    }
    if (check_selected()) {
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

/**********
 * Step 2 *
 **********/

var QuestionnaireExperience2 = function () {
  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: "q_experience2",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    record_responses();
    psiTurk.recordTrialData({ phase: "q_experience2", status: "end" });
    // Depending on 2D_Q2 go into different questionnaire: linger rating 1:
    if ($("#linger_rating").val() == "1") {
      finish_questionnaire_experience();
    } else {
      currentview = new QuestionnaireExperience3();
    }
  };

  psiTurk.showPage("questionnaires/experience2.html");
  psiTurk.recordTrialData({ phase: "q_experience2", status: "begin" });

  // debug skip
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  // Define function to prevent copy, paste, and cut
  // ref: https://jsfiddle.net/lesson8/ZxKdp/
  $("input,textarea").bind("cut copy paste", function (e) {
    e.preventDefault(); //disable cut,copy,paste
  });

  function show_warning() {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  }

  $("#submit").on("click", function () {
    show_warning();
  });

  check_selected = function () {
    // standard fields
    if (
      exp_condition == "button_press_suppress" ||
      exp_condition == "suppress"
    ) {
      if (!($("select.changed").length === $("select.qselect").length)) {
        return false;
      }

      // Textbox counts if more than 2 characters are written
      if ($("#wcg_diff_suppress").val().trim().length < 3) {
        return false;
      }
      if ($("#wcg_strategy_after_fail").val().trim().length < 3) {
        return false;
      }
    } else {
      if (!($("select.changed").length === $("select.qselect").length - 2)) {
        return false;
      }
    }

    // Textbox counts if more than 2 characters are written
    if ($("#wcg_diff_general").val().trim().length < 3) {
      return false;
    }

    return true;
  };

  // show suppression questions
  if (exp_condition == "button_press_suppress" || exp_condition == "suppress") {
    $(".suppress").show();
  }

  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  $(".qelement").on("change", function () {
    if ($(this).prop("nodeName").toLowerCase() == "select") {
      $(this).addClass("changed");
    }
    if (check_selected()) {
      console.debug("All selected: enabling button");
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

/**********
 * Step 3 *
 **********/

var QuestionnaireExperience3 = function () {
  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: "q_experience3",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    $("#submit").off();
    record_responses();
    psiTurk.recordTrialData({ phase: "q_experience3", status: "end" });
    currentview = QuestionnaireExperience4();
  };

  psiTurk.showPage("questionnaires/experience3.html");
  psiTurk.recordTrialData({ phase: "q_experience3", status: "begin" });

  // debug skip
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  // Define function to prevent copy, paste, and cut
  // ref: https://jsfiddle.net/lesson8/ZxKdp/
  $("input,textarea").bind("cut copy paste", function (e) {
    e.preventDefault(); //disable cut,copy,paste
  });

  function show_warning() {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  }

  $("#submit").on("click", function () {
    show_warning();
  });

  check_selected = function () {
    // standard fields
    if (!($("select.changed").length === $("select.qselect").length)) {
      return false;
    }

    // Textbox counts if more than 2 characters are written
    if ($("#volition_explanation").val().trim().length < 3) {
      return false;
    }

    return true;
  };

  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  $(".qelement").on("change", function () {
    if ($(this).prop("nodeName").toLowerCase() == "select") {
      $(this).addClass("changed");
    }
    if (check_selected()) {
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

/**********
 * Step 4 *
 **********/

var QuestionnaireExperience4 = function () {
  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: "q_experience4",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    record_responses();
    psiTurk.recordTrialData({ phase: "q_experience4", status: "end" });
    finish_questionnaire_experience();
  };

  psiTurk.showPage("questionnaires/experience4.html");
  psiTurk.recordTrialData({ phase: "q_experience4", status: "begin" });

  // debug skip
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  // Define function to prevent copy, paste, and cut
  // ref: https://jsfiddle.net/lesson8/ZxKdp/
  $("input,textarea").bind("cut copy paste", function (e) {
    e.preventDefault(); //disable cut,copy,paste
  });

  function show_warning() {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  }

  $("#submit").on("click", function () {
    show_warning();
  });

  check_selected = function () {
    // standard fields
    if (!($("select.changed").length === $("select.qselect").length)) {
      return false;
    }

    // Textbox counts if more than 2 characters are written
    if ($("#wcg_diff_explanation").val().trim().length < 3) {
      return false;
    }

    return true;
  };

  // enable button once all questions are answered
  // https://stackoverflow.com/a/74058636
  $(".qelement").on("change", function () {
    if ($(this).prop("nodeName").toLowerCase() == "select") {
      $(this).addClass("changed");
    }
    if (check_selected()) {
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
