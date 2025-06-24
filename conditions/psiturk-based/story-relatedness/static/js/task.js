/*
 * Requires:
 *     psiturk.js
 *     utils.js
 *     story_var.js
 *     permutations_var.js
 *     words_var.js
 */

// Flags
const WORD_RATE_DELAY_BUTTON_ACTIVE_FIRST = 700; // first presentation of word
const WORD_RATE_DELAY_BUTTON_ACTIVE_SECOND = 500; // second presentation of word
const SPR_DELAY_KEY_ACTIVE = 100;

// Flags affected by debug override
var instruction_delay = 2000;
var instruction_delay_short = 0;

// debug override
if (mode == "debug") {
  instruction_delay = 0;
  instruction_delay_short = 0;
}

const INSTRUCTION_DELAY = instruction_delay;
const INSTRUCTION_DELAY_SHORT = instruction_delay_short;

// indices for word rating conditions
const WORD_ARRAY_CONDITION_STARTS = [
  0, 356, 712, 1068, 1424, 1780, 2136, 2492, 2848, 3204, 3560, 3916, 4272, 4628,
  4984, 5340, 5696, 6052, 6408,
];
const WORD_ARRAY_CONDITION_ENDS = [
  356, 712, 1068, 1424, 1780, 2136, 2492, 2848, 3204, 3560, 3916, 4272, 4628,
  4984, 5340, 5696, 6052, 6408, 6754,
];

// Initalize psiturk object
var psiTurk = new PsiTurk(uniqueId, adServerLoc, mode);

// psiturk code will make sure to balance across conditions/counterbalances
var mycondition = condition; // selects word permutation
var mycounterbalance = counterbalance; // selects section within word permutation

// Select wich question is asked first
var theme_question_first = (condition + counterbalance) % 2 == 0;

// All pages to be loaded
var pages = [
  "instructions/instruct-1-0.html",
  "instructions/instruct-1-1.html",
  "instructions/instruct-2-0.html",
  "instructions/instruct-2-1.html",
  "instructions/instruct-3-0-0.html",
  "instructions/instruct-3-0-1.html",
  "instructions/instruct-3-1.html",
  "spr.html",
  "instructions/instruct-3-2.html",
  "instructions/instruct-4-0.html",
  "instructions/instruct-4-1.html",
  "instructions/instruct-4-1-1.html",
  "instructions/instruct-4-1-2.html",
  "word_rating.html",
  "instructions/instruct-4-2.html",
  "questionnaire.html",
  "instructions/instruct-5.html",
  "demographic_survey.html",
  "instructions/instruct-6.html",
];

// In javascript, defining a function as `async` makes it return  a `Promise`
// that will "resolve" when the function completes. Below, `init` is assigned to be the
// *returned value* of immediately executing an anonymous async function.
// This is done by wrapping the async function in parentheses, and following the
// parentheses-wrapped function with `()`.
// Therefore, the code within the arrow function (the code within the curly brackets) immediately
// begins to execute when `init is defined. In the example, the `init` function only
// calls `psiTurk.preloadPages()` -- which, as of psiTurk 3, itself returns a Promise.
//
// The anonymous function is defined using javascript "arrow function" syntax.
const init = (async () => {
  await psiTurk.preloadPages(pages);
})();

var instructionPages = [
  // add as a list as many pages as you like
  "instructions/instruct-1-0.html",
  "instructions/instruct-1-1.html",
  "instructions/instruct-2-0.html",
  "instructions/instruct-2-1.html",
  "instructions/instruct-3-0-0.html",
  "instructions/instruct-3-0-1.html",
  "instructions/instruct-3-1.html",
];

/********************
 * HTML manipulation
 *
 * All HTML files in the templates directory are requested
 * from the server when the PsiTurk object is created above. We
 * need code to get those pages from the PsiTurk object and
 * insert them into the document.
 *
 ********************/

/**********************
 * Self paced reading *
 *********************/

var SelfPacedReading = function () {
  var listening = false;
  var index = 0;
  var current_sentence;
  var sentence_on;

  function finish_task() {
    $("body").unbind("keydown", response_handler);
    psiTurk.recordTrialData({ phase: "spr", status: "end" });
    psiTurk.doInstructions(["instructions/instruct-3-2.html"], function () {
      currentview = new RatingInstructions();
    });
  }

  function show_sentence() {
    current_sentence = story.row[index];
    d3.select("#sentence").text(current_sentence.Story);
    sentence_on = new Date().getTime();
    setTimeout(function () {
      listening = true;
    }, SPR_DELAY_KEY_ACTIVE);
  }

  function response_handler(e) {
    if (!listening) return;
    if (e.keyCode != 32) return;

    listening = false;

    // save reading time
    current_sentence["phase"] = "spr";
    current_sentence["status"] = "ongoing";
    current_sentence["rt"] = new Date().getTime() - sentence_on;
    psiTurk.recordTrialData(current_sentence);

    // update sentence
    index++;
    if (index == story.row.length) return finish_task();
    show_sentence();
  }

  // load initial display
  psiTurk.showPage("spr.html");
  psiTurk.recordTrialData({ phase: "spr", status: "begin" });

  // register click
  $("body").focus().keydown(response_handler);

  // debug skip
  if (mode == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").click(function () {
      finish_task();
    });
  }

  // show first sentence
  show_sentence();
};

/***************
 * Word rating *
 ***************/

var RatingInstructions = function () {
  psiTurk.doInstructions(
    [
      "instructions/instruct-4-0.html",
      "instructions/instruct-4-1.html",
      "instructions/instruct-4-1-1.html",
      "instructions/instruct-4-1-2.html",
    ],
    function () {
      currentview = new WordRating();
    }
  );
};

var WordRating = function () {
  var listening = false;
  var index_current_word;
  var current_word;
  var word_on;
  var progress_percentage;
  var next_question_theme;
  var questions_asked = 0;

  function finish_task() {
    psiTurk.recordTrialData({ phase: "rating", status: "end" });
    psiTurk.doInstructions(["instructions/instruct-4-2.html"], function () {
      currentview = new Questionnaire();
    });
  }

  function register_buttons() {
    // register key handler
    $(".likert")
      .find("button")
      .on("click", function (event) {
        if (!listening) return;
        listening = false;
        record_response(event.target.value);
      });
  }

  // Ask moment question
  function moment_relatedness() {
    // show relevant elements
    d3.select("#question").html(
      '<p>How related is the word to a <b>specific moment</b> within the story?</p><p id="question-example">(e.g. the word reminds you of particular details in the story)</p>'
    );
    d3.select("#query").html(
      '<p id="hint"><i>click a button to indicate your choice</i></p> <div class="likert"> <button id="b1" class="btn btn-default" value="1" disabled> 1 <br /> least related <br /> (moment) </button> <button id="b2" class="btn btn-default" value="2" disabled>2</button><button id="b3" class="btn btn-default" value="3" disabled>3</button><button id="b4" class="btn btn-default" value="4" disabled>4</button><button id="b5" class="btn btn-default" value="5" disabled>5</button><button id="b6" class="btn btn-default" value="6" disabled>6</button><button id="b7" class="btn btn-default" value="7" disabled> 7 <br />most related <br /> (moment)</button></div>'
    );
    register_buttons();
  }

  // Ask theme question
  function theme_relatedness() {
    // show relevant elements
    d3.select("#question").html(
      '<p>How related is the word to a <b>general theme or mood</b> of the story?<p id="question-example">(e.g. you feel the word is related, even though not to a specific moment)<p>'
    );
    d3.select("#query").html(
      '<p id="hint"><i>click a button to indicate your choice</i></p> <div class="likert"> <button id="b1" class="btn btn-default" value="1" disabled> 1 <br /> least related <br /> (theme) </button> <button id="b2" class="btn btn-default" value="2" disabled>2</button><button id="b3" class="btn btn-default" value="3" disabled>3</button><button id="b4" class="btn btn-default" value="4" disabled>4</button><button id="b5" class="btn btn-default" value="5" disabled>5</button><button id="b6" class="btn btn-default" value="6" disabled>6</button><button id="b7" class="btn btn-default" value="7" disabled> 7 <br />most related <br /> (theme)</button></div>'
    );
    register_buttons();
  }

  function next_question() {
    var timeout;

    // Inactivate buttons
    $("button").attr("disabled", true);
    if (next_question_theme) {
      theme_relatedness();
      next_question_theme = false;
    } else {
      moment_relatedness();
      next_question_theme = true;
    }
    if (questions_asked == 2) {
      questions_asked = 0;
      if (permutation.length == 0) return finish_task();
      next_word();
    }
    questions_asked++;
    // Update timer
    word_on = new Date().getTime();
    // Delay button activity for X milliseconds, depending on first or second
    // presentation of word.
    if (questions_asked == 1) timeout = WORD_RATE_DELAY_BUTTON_ACTIVE_FIRST;
    else timeout = WORD_RATE_DELAY_BUTTON_ACTIVE_SECOND;
    setTimeout(function () {
      $("button").attr("disabled", false);
    }, timeout);
    listening = true;
  }

  function next_word() {
    // Update word
    index_current_word = permutation.shift();
    current_word = words[index_current_word];
    d3.select("#word").text(current_word.word);
    // Update progress bar
    progress_percentage = 100 - (100 * permutation.length) / n_words_total;
    $("#pbar").css("width", progress_percentage + "%");
    $("#pbar").attr("aria-valuenow", progress_percentage);
  }

  function record_response(index) {
    var output_word = {};
    Object.assign(output_word, current_word);
    output_word["phase"] = "rating";
    output_word["status"] = "ongoing";
    output_word["rt"] = new Date().getTime() - word_on;
    // next_question_theme == true => current question moment
    if (next_question_theme) output_word["question_type"] = "moment";
    else output_word["question_type"] = "theme";
    output_word["response"] = index;
    output_word["perm_idx"] = index_current_word;
    psiTurk.recordTrialData(output_word);
    console.log(output_word);

    next_question();
  }

  // load correct permutation
  var permutation = permutations[mycondition].slice(
    WORD_ARRAY_CONDITION_STARTS[mycounterbalance],
    WORD_ARRAY_CONDITION_ENDS[mycounterbalance]
  );
  n_words_total = permutation.length;

  // load page
  psiTurk.showPage("word_rating.html");
  psiTurk.recordTrialData({ phase: "rating", status: "begin" });

  // debug skip
  if (mode == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").click(function () {
      finish_task();
    });
  }

  // Set variables appropriatly
  next_question_theme = theme_question_first;
  questions_asked = 2;

  // start the rating
  next_question();
};

/****************
 * Questionnaire *
 ****************/

var Questionnaire = function () {
  function record_responses() {
    $("select.qselect").each(function () {
      psiTurk.recordTrialData({
        phase: "questionnaire",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    psiTurk.recordTrialData({ phase: "questionnaire", status: "end" });
    record_responses();
    psiTurk.doInstructions(["instructions/instruct-5.html"], function () {
      currentview = new DemographicSurvey();
    });
  };

  psiTurk.showPage("questionnaire.html");
  psiTurk.recordTrialData({ phase: "questionnaire", status: "begin" });

  // debug skip
  if (mode == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").click(function () {
      finish_task();
    });
  }

  $("#submit").click(function () {
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
      $("#submit").click(function () {
        finish_task();
      });
    } else {
      console.debug("One or more not selected yet!!");
    }
  });
};

/**************
 * final page *
 **************/

var DemographicSurvey = function () {
  var error_message =
    "<h1>Oops!</h1><p>Something went wrong submitting your study. This might happen if you lose your internet connection. Press the button to resubmit.</p><button id='resubmit'>Resubmit</button>";

  // functions for data submission to server
  prompt_resubmit = function () {
    document.body.innerHTML = error_message;
    $("#resubmit").click(resubmit);
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

  // task functions
  function record_responses() {
    $("select.qselect").each(function () {
      psiTurk.recordTrialData({
        phase: "demographic_survey",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
    $("conditional_text").each(function () {
      psiTurk.recordTrialData({
        phase: "demographic_survey",
        status: "ongoing",
        question: this.id,
        answer: this.value,
      });
    });
  }

  finish_task = function () {
    psiTurk.recordTrialData({ phase: "demographic_survey", status: "end" });
    record_responses();
    psiTurk.saveData({
      success: save_success,
      error: prompt_resubmit,
    });
  };

  psiTurk.showPage("demographic_survey.html");
  psiTurk.recordTrialData({ phase: "demographic_survey", status: "begin" });

  // debug skip
  if (mode == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").click(function () {
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
      $("#submit").click(function () {
        finish_task();
      });
    } else {
      console.debug("Something is not filled.");
      $("#submit").click(function () {
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

  $("#submit").click(function () {
    $("#warning").html(
      '<div class="alert alert-danger"><i>Please answer all questions!</i></div>'
    );
  });
};

// var FinalPage = function () {
//   psiTurk.doInstructions(["instructions/instruct-6.html"], function () {
//     psiTurk.completeHIT();
//   });
// };

// Task object to keep track of the current phase
var currentview;

/*******************
 * Run Task
 ******************/
// In this example `task.js file, an anonymous async function is bound to `window.on('load')`.
// The async function `await`s `init` before continuing with calling `psiturk.doInstructions()`.
// This means that in `init`, you can `await` other Promise-returning code to resolve,
// if you want it to resolve before your experiment calls `psiturk.doInstructions()`.

// The reason that `await psiTurk.preloadPages()` is not put directly into the
// function bound to `window.on('load')` is that this would mean that the pages
// would not begin to preload until the window had finished loading -- an unnecessary delay.
$(window).on("load", async () => {
  await init;

  psiTurk.finishInstructions();
  psiTurk.doInstructions(
    instructionPages, // a list of pages you want to display in sequence
    function () {
      currentview = new SelfPacedReading();
    } // what you want to do when you are done with instructions
  );
});
