var QuestionnaireDoublePress = function (pre_or_post) {
  let phase;
  let html;

  if (pre_or_post == "pre") {
    phase = "q_double_press_pre";
    html = "questionnaires/double_press_pre.html";
  } else {
    phase = "q_double_press_post";
    html = "questionnaires/double_press_post.html";
  }

  function record_responses() {
    $(".qelement").each(function () {
      psiTurk.recordTrialData({
        phase: phase,
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    record_responses();
    psiTurk.recordTrialData({ phase: phase, status: "end" });
    if (pre_or_post == "pre") finish_double_press_pre();
    else finish_double_press_post();
  };

  psiTurk.showPage(html);
  psiTurk.recordTrialData({ phase: phase, status: "begin" });

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

  check_selected = function () {
    if (!($("select.changed").length === $("select.qselect").length)) {
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
