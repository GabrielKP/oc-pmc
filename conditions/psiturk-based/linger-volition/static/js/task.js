/*
 * Requires:
 *     psiturk.js
 *     utils.js
 *     variables/story_var.js
 *     variables/permutations_var.js
 *     variables/words_var.js
 *     experiments/comprehension.js
 *     experiments/demographics.js
 *     experiments/open.js
 *     experiments/transportation.js
 *     experiments/word_chain_game_and_story_reading.js
 */

// Flags
const WORD_RATE_DELAY_BUTTON_ACTIVE_FIRST = 700; // first presentation of word
const WORD_RATE_DELAY_BUTTON_ACTIVE_SECOND = 500; // second presentation of word
const SPR_DELAY_KEY_ACTIVE = 100;
// Set first entry -1 if it is controlled by time [all others are controlled by words]

// Flags affected by debug override
var instruction_delay = 2000;
var instruction_delay_short = 0;
var time_limit_post = 180000;
var time_limit_pre = 180000;

// debug override
if (mode == "debug") {
  instruction_delay = 0;
  instruction_delay_short = 0;
  time_limit_post = 10000;
  time_limit_pre = 10000;
}

var mode_shared = mode;

const INSTRUCTION_DELAY = instruction_delay;
const INSTRUCTION_DELAY_SHORT = instruction_delay_short;

// Initalize psiturk object
var psiTurk = new PsiTurk(uniqueId, adServerLoc, mode);

// Only relevant if exp_condition == "button_press_both"
// 0 button_press (no suppress)
// 1 button_press_suppress
var sub_condition = condition;

// EXPERIMENT CONDITIONS
// - suppress: ask participants to suppress thoughts about the story
// - button_press_both: evenly distribute participants across button_press & button_press_suppress
// - button_press: participant has to double-press space bar after thinking about food/story
// - button_press_suppress: participant has to double-press space bar after thinking about food/story
//                          whilst suppressing thoughts about food/story
// The condition is specifified in '.env' as EXP_CONDTION
var exp_condition = undefined;
var exp_condition_answer = undefined;
exp_condition_answer = $.get("/get_exp_condition");

// All pages to be loaded
let temp_pages = [
  "instructions/exp_condition/instruct-1-0.html",
  "instructions/exp_condition/instruct-1-1.html",
  "instructions/exp_condition/instruct-1-2.html",
  "instructions/exp_condition/instruct-2-0.html",
  "instructions/exp_condition/instruct-3-3.html",
  "instructions/exp_condition/instruct-4-0.html",
  "instructions/exp_condition/instruct-4-1.html",
  "instructions/exp_condition/instruct-5-0.html",
  "instructions/exp_condition/instruct-5-2.html",
  "instructions/exp_condition/instruct-5-3.html",
  "instructions/exp_condition/instruct-6-0.html",
  "instructions/exp_condition/instruct-7-0.html",
  "story_reading.html",
  "word_chain_game.html",
  "questionnaires/double_press_pre.html",
  "questionnaires/double_press_post.html",
  "questionnaires/transportation.html",
  "questionnaires/comprehension.html",
  "questionnaires/experience1.html",
  "questionnaires/experience2.html",
  "questionnaires/experience3.html",
  "questionnaires/experience4.html",
  "questionnaires/demographics.html",
  "questionnaires/open.html",
  // non-shared button_press_suppress
  "instructions/button_press_suppress/instruct-3-0-0.html",
  "instructions/button_press_suppress/instruct-3-0-1.html",
  "instructions/button_press_suppress/instruct-3-0-2.html",
  "instructions/button_press_suppress/instruct-3-1-0.html",
  "instructions/button_press_suppress/instruct-3-2-0.html",
  "instructions/button_press_suppress/instruct-3-2-1.html",
  "instructions/button_press_suppress/instruct-5-1-0.html",
  "instructions/button_press_suppress/instruct-5-1-1.html",
  // non-shared button_press
  "instructions/button_press/instruct-3-0-0.html",
  "instructions/button_press/instruct-3-0-1.html",
  "instructions/button_press/instruct-3-0-2.html",
  "instructions/button_press/instruct-3-1-0.html",
  "instructions/button_press/instruct-3-2-0.html",
  "instructions/button_press/instruct-3-2-1.html",
  "instructions/button_press/instruct-5-1-0.html",
  "instructions/button_press/instruct-5-1-1.html",
  // non-shared suppress
  "instructions/suppress/instruct-3-0.html",
  "instructions/suppress/instruct-3-1.html",
  "instructions/suppress/instruct-3-2.html",
  "instructions/suppress/instruct-5-1.html",
];

let pages = [];
const init = (async () => {
  await exp_condition_answer;
  exp_condition = exp_condition_answer["responseText"];

  console.debug("sub_condition: " + sub_condition);
  if (exp_condition == "button_press_both") {
    if (sub_condition == 0) {
      exp_condition = "button_press";
    } else {
      exp_condition = "button_press_suppress";
    }
  }

  let fill_val = exp_condition;

  // fill in condition
  let page;
  for (page of temp_pages) {
    pages.push(page.replace("exp_condition", fill_val));
  }

  await psiTurk.preloadPages(pages);
})();

/***************************
 * Experiment Flow Control *
 ***************************/

// Word chain game practice ->
function finish_word_chain_game_practice() {
  if (exp_condition == "button_press_suppress") {
    psiTurk.doInstructions(
      [
        "instructions/button_press_suppress/instruct-3-1-0.html",
        "instructions/button_press_suppress/instruct-3-2-0.html",
        "instructions/button_press_suppress/instruct-3-2-1.html",
        "instructions/button_press_suppress/instruct-3-3.html",
      ],
      function () {
        currentview = new WordChainGame("pre");
      }
    );
  } else if (exp_condition == "button_press") {
    psiTurk.doInstructions(
      [
        "instructions/button_press/instruct-3-1-0.html",
        "instructions/button_press/instruct-3-2-0.html",
        "instructions/button_press/instruct-3-2-1.html",
        "instructions/button_press/instruct-3-3.html",
      ],
      function () {
        currentview = new WordChainGame("pre");
      }
    );
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
}

// Word chain game pre ->
function finish_word_chain_game_pre() {
  if (exp_condition == "suppress") {
    psiTurk.doInstructions(
      [
        "instructions/suppress/instruct-4-0.html",
        "instructions/suppress/instruct-4-1.html",
      ],
      function () {
        currentview = new StoryReading();
      }
    );
  } else if (exp_condition == "button_press_suppress") {
    currentview = new QuestionnaireDoublePress("pre");
  } else if (exp_condition == "button_press") {
    currentview = new QuestionnaireDoublePress("pre");
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
}

// Double press pre ->
function finish_double_press_pre() {
  if (exp_condition == "button_press_suppress") {
    psiTurk.doInstructions(
      [
        "instructions/button_press_suppress/instruct-4-0.html",
        "instructions/button_press_suppress/instruct-4-1.html",
      ],
      function () {
        currentview = new StoryReading();
      }
    );
  } else if (exp_condition == "button_press") {
    psiTurk.doInstructions(
      [
        "instructions/button_press/instruct-4-0.html",
        "instructions/button_press/instruct-4-1.html",
      ],
      function () {
        currentview = new StoryReading();
      }
    );
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
}

// Story reading ->
function finish_story_reading() {
  if (exp_condition == "suppress") {
    psiTurk.doInstructions(
      [
        "instructions/suppress/instruct-5-0.html",
        "instructions/suppress/instruct-5-1.html",
        "instructions/suppress/instruct-5-2.html",
        "instructions/suppress/instruct-5-3.html",
      ],
      function () {
        currentview = new WordChainGame("post");
      }
    );
  } else if (exp_condition == "button_press_suppress") {
    psiTurk.doInstructions(
      [
        "instructions/button_press_suppress/instruct-5-0.html",
        "instructions/button_press_suppress/instruct-5-1-0.html",
        "instructions/button_press_suppress/instruct-5-1-1.html",
        "instructions/button_press_suppress/instruct-5-2.html",
        "instructions/button_press_suppress/instruct-5-3.html",
      ],
      function () {
        currentview = new WordChainGame("post");
      }
    );
  } else if (exp_condition == "button_press") {
    psiTurk.doInstructions(
      [
        "instructions/button_press/instruct-5-0.html",
        "instructions/button_press/instruct-5-1-0.html",
        "instructions/button_press/instruct-5-1-1.html",
        "instructions/button_press/instruct-5-2.html",
        "instructions/button_press/instruct-5-3.html",
      ],
      function () {
        currentview = new WordChainGame("post");
      }
    );
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
}

// Word chain game post ->
function finish_word_chain_game_post() {
  if (exp_condition == "suppress") {
    psiTurk.doInstructions(
      ["instructions/suppress/instruct-6-0.html"],
      function () {
        currentview = new QuestionnaireTransportation();
      }
    );
  } else if (exp_condition == "button_press_suppress") {
    currentview = new QuestionnaireDoublePress("post");
  } else if (exp_condition == "button_press") {
    currentview = new QuestionnaireDoublePress("post");
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
}

// Double press post ->
function finish_double_press_post() {
  if (exp_condition == "button_press_suppress") {
    psiTurk.doInstructions(
      ["instructions/button_press_suppress/instruct-6-0.html"],
      function () {
        currentview = new QuestionnaireTransportation();
      }
    );
  } else if (exp_condition == "button_press") {
    psiTurk.doInstructions(
      ["instructions/button_press/instruct-6-0.html"],
      function () {
        currentview = new QuestionnaireTransportation();
      }
    );
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
}

// Transportation ->
function finish_questionnaire_transportation() {
  currentview = new QuestionnaireComprehension();
}

// Comprehension ->
function finish_questionnaire_comprehension() {
  currentview = new QuestionnaireExperience1();
}

// Experiences (Volition & others) ->
function finish_questionnaire_experience() {
  if (exp_condition == "suppress") {
    psiTurk.doInstructions(
      ["instructions/suppress/instruct-7-0.html"],
      function () {
        currentview = new QuestionnaireDemographics();
      }
    );
  } else if (exp_condition == "button_press_suppress") {
    psiTurk.doInstructions(
      ["instructions/button_press_suppress/instruct-7-0.html"],
      function () {
        currentview = new QuestionnaireDemographics();
      }
    );
  } else if (exp_condition == "button_press") {
    psiTurk.doInstructions(
      ["instructions/button_press/instruct-7-0.html"],
      function () {
        currentview = new QuestionnaireDemographics();
      }
    );
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
}

// Instruction Phase 3 ->
function finish_questionnaire_demographics() {
  currentview = new QuestionnaireOpen();
}

// Define initial set of instructions for different conditions.
var instruction_pages_suppress = [
  "instructions/suppress/instruct-1-0.html",
  "instructions/suppress/instruct-1-1.html",
  "instructions/suppress/instruct-1-2.html",
  "instructions/suppress/instruct-2-0.html",
  "instructions/suppress/instruct-3-0.html",
  "instructions/suppress/instruct-3-1.html",
  "instructions/suppress/instruct-3-2.html",
  "instructions/suppress/instruct-3-3.html",
];
var instruction_pages_button_press = [
  "instructions/button_press/instruct-1-0.html",
  "instructions/button_press/instruct-1-1.html",
  "instructions/button_press/instruct-1-2.html",
  "instructions/button_press/instruct-2-0.html",
  "instructions/button_press/instruct-3-0-0.html",
  "instructions/button_press/instruct-3-0-1.html",
  "instructions/button_press/instruct-3-0-2.html",
];
var instruction_pages_button_press_suppress = [
  "instructions/button_press_suppress/instruct-1-0.html",
  "instructions/button_press_suppress/instruct-1-1.html",
  "instructions/button_press_suppress/instruct-1-2.html",
  "instructions/button_press_suppress/instruct-2-0.html",
  "instructions/button_press_suppress/instruct-3-0-0.html",
  "instructions/button_press_suppress/instruct-3-0-1.html",
  "instructions/button_press_suppress/instruct-3-0-2.html",
];

// Task object to keep track of the current phase
var currentview;

/*******************
 * Run Task
 ******************/

$(window).on("load", async () => {
  await init;

  psiTurk.finishInstructions();

  console.debug("exp_condition: " + exp_condition);
  psiTurk.recordTrialData({
    phase: "initialization",
    condition: exp_condition,
  });

  if (exp_condition == "suppress") {
    psiTurk.doInstructions(instruction_pages_suppress, function () {
      currentview = new WordChainGame("pre");
    });
  } else if (exp_condition == "button_press_suppress") {
    psiTurk.doInstructions(
      instruction_pages_button_press_suppress,
      function () {
        currentview = new WordChainGame("practice", 10);
      }
    );
  } else if (exp_condition == "button_press") {
    psiTurk.doInstructions(instruction_pages_button_press, function () {
      currentview = new WordChainGame("practice", 10);
    });
  } else {
    console.debug("Invalid exp_condition: " + exp_condition);
  }
});
