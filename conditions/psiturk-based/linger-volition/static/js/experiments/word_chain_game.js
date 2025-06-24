/*******************
 * Word chain game *
 *******************/

var WordChainGame = function (pre_or_post, practice_word_count = 3) {
  let listening = false;
  let word_count = 0;
  let word_start_time;
  let word_end_time;
  let word_text;
  let word_key_chars;
  let word_key_codes;
  let word_key_onsets;
  let word_double_press_count;
  let key_start_time;
  let key_end_time;
  let mode;
  let total_double_press_count = 0;
  let last_spacebar_press = null; // To keep track of valid double presses
  const DOUBLE_PRESS_THRESHOLD = 1000; // Time in milliseconds for double press detection

  function finish_task() {
    $("body").unbind("keydown", response_handler);
    psiTurk.recordTrialData({
      phase: "wcg",
      status: "ongoing",
      mode: "double_press",
      double_press: "total",
      pre_or_post: pre_or_post,
      total_double_press_count: total_double_press_count,
    });
    psiTurk.recordTrialData({
      phase: "wcg",
      status: "end",
      pre_or_post: pre_or_post,
    });
    if (pre_or_post == "practice") finish_word_chain_game_practice();
    else if (pre_or_post == "pre") finish_word_chain_game_pre();
    else if (pre_or_post == "post") finish_word_chain_game_post();
    else console.error("Invalid pre_or_post: " + pre_or_post);
  }

  function fade_cue(text, time_until_fade_out = 500, time_fade_out = 500) {
    $("#cue").html(text);
    $(".stim-div").fadeTo(250, 1);
    setTimeout(function () {
      $(".stim-div").fadeTo(time_fade_out, 0);
    }, time_until_fade_out);
  }

  function save_word() {
    var submit_object = {};
    word_text = $("#qinput").val();
    submit_object["phase"] = "wcg";
    submit_object["status"] = "ongoing";
    submit_object["mode"] = "word";
    submit_object["word_text"] = word_text;
    submit_object["word_count"] = word_count;
    submit_object["word_time"] = word_end_time - word_start_time;
    submit_object["word_key_chars"] = word_key_chars;
    submit_object["word_key_codes"] = word_key_codes;
    submit_object["word_key_onsets"] = word_key_onsets;
    submit_object["word_double_press_count"] = word_double_press_count;
    submit_object["pre_or_post"] = pre_or_post;
    psiTurk.recordTrialData(submit_object);
  }

  function ready_word_variables() {
    word_key_chars = [];
    word_key_codes = [];
    word_key_onsets = [];
    word_double_press_count = 0;
    word_start_time = new Date().getTime();
    key_start_time = new Date().getTime();
    listening = true;
  }

  function show_cue_new_textbox() {
    $("#qinput").val("");
    fade_cue(word_text.toUpperCase());
    ready_word_variables();
  }

  /*****
   * This function switches to the appropriate next mode,
   * dependent on the previous mode. It will then initiate
   * the correct display of the next mode.
   */
  function show_next() {
    if (
      exp_condition == "suppress" ||
      exp_condition == "button_press_suppress" ||
      exp_condition == "button_press"
    ) {
      show_next_exp_suppress_and_button_press();
    } else {
      console.error("Invalid exp_condition: " + exp_condition);
    }
  }

  function show_next_exp_suppress_and_button_press() {
    if (mode == "switch_to_story") {
      finish_task();
    } else {
      show_cue_new_textbox();
    }
  }

  function response_handler(key) {
    if (!listening) return;
    listening = false;
    if (key.keyCode == 13) {
      // "ENTER" - key

      if ($("#qinput").val() == "") {
        // do not submit if textbox is empty
        listening = true;
        key.preventDefault();
        return;
      }

      // record keystroke
      key_end_time = new Date().getTime();
      word_key_chars.push(String.fromCharCode(key.keyCode));
      word_key_codes.push(key.keyCode);
      word_key_onsets.push(key_end_time - key_start_time);

      // Submit data to psiturk
      word_end_time = new Date().getTime();
      word_text = $("#qinput").val();
      save_word();
      word_count++;

      // if practice, check for word count
      if (pre_or_post == "practice" && word_count >= practice_word_count) {
        finish_task();
      }

      //Reset the space bar presses for the next word
      word_spacebar_presses = 0;

      // disable enter key's default function (keeps text box unchanged after pressing enter)
      key.preventDefault();

      show_next();
    } else if (key.keyCode == 32) {
      key.preventDefault();
      // handle the space bar key in button press condition
      if (
        (exp_condition == "button_press_suppress" ||
          exp_condition == "button_press") &&
        !(pre_or_post == "practice")
      ) {
        current_time = new Date().getTime();
        // Only trigger within double press threshold
        if (
          last_spacebar_press != null &&
          current_time - last_spacebar_press <= DOUBLE_PRESS_THRESHOLD
        ) {
          word_double_press_count++;
          total_double_press_count++;
          console.log("Double press! Count: " + total_double_press_count);
          double_press_time = new Date().getTime();
          psiTurk.recordTrialData({
            phase: "wcg",
            status: "ongoing",
            mode: "double_press",
            double_press: "occurrence",
            current_double_press_count: total_double_press_count,
            time_since_last_word_start: double_press_time - word_start_time,
            word_text: $("#qinput").val(),
            word_count: word_count,
            word_key_chars: word_key_chars.slice(),
            word_key_codes: word_key_codes.slice(),
            word_key_onsets: word_key_onsets.slice(),
            word_double_press_count: word_double_press_count,
            pre_or_post: pre_or_post,
          });
          // reset to avoid double counting
          last_spacebar_press = null;
          // visual cue
          $("#double-space-feedback")
            .stop(true)
            .fadeTo(0, 1, () => {
              $("#double-space-feedback").fadeTo(1000, 0);
            });
        } else {
          last_spacebar_press = current_time;
        }
      }
      listening = true;
    } else if (
      key.keyCode == 192 ||
      key.keyCode == 219 ||
      key.keyCode == 220 ||
      key.keyCode == 211 ||
      key.keyCode == 59 ||
      key.keyCode == 222 ||
      key.keyCode == 188 ||
      key.keyCode == 190 ||
      key.keyCode == 191 ||
      key.keyCode == 61
    ) {
      // DISABLED keys: non-alphanumeric characters
      key.preventDefault();
      listening = true;
    } else {
      // "NORMAL" keys: save key char, code and time
      key_end_time = new Date().getTime();
      word_key_chars.push(String.fromCharCode(key.keyCode));
      word_key_codes.push(key.keyCode);
      word_key_onsets.push(key_end_time - key_start_time);
      key_start_time = new Date().getTime();
      listening = true;
    }
  }

  // load initial display
  psiTurk.showPage("word_chain_game.html");
  psiTurk.recordTrialData({
    phase: "wcg",
    status: "begin",
    pre_or_post: pre_or_post,
  });

  // Any click onscreen autofocuses to textbox
  $(function () {
    $("html").on("click", function () {
      $("#qinput").focus();
    });
  });

  // Define function to prevent copy, paste, and cut
  // ref: https://jsfiddle.net/lesson8/ZxKdp/
  $("input,textarea").bind("cut copy paste", function (e) {
    e.preventDefault(); //disable cut,copy,paste
  });

  // register event listener
  $("body").focus().keydown(response_handler);

  // debug skip
  console.debug(mode_shared);
  if (mode_shared == "debug") {
    d3.select("#skip").html(
      "<button id='skipbutton' class='btn btn-default'>SKIP</button>"
    );
    $("#skipbutton").on("click", function () {
      finish_task();
    });
  }

  // Draw circle
  let canvas = document.getElementById("canvas-circle");
  let ctx = canvas.getContext("2d");
  ctx.beginPath();
  ctx.arc(50, 30, 20, 0, 2 * Math.PI);
  ctx.fillStyle = "lightblue";
  ctx.fill();

  // start experiment
  if (pre_or_post == "practice") {
    $("#cue").html("Enter a word to begin!");
    mode = "word_chain_game";
    ready_word_variables();
  } else if (
    exp_condition == "suppress" ||
    exp_condition == "button_press_suppress" ||
    exp_condition == "button_press"
  ) {
    $("#cue").html("Enter a word to begin!");
    // Timer for pre FA
    setTimeout(function () {
      mode = "switch_to_story";
    }, time_limit_pre);

    mode = "word_chain_game";
    ready_word_variables();
  } else {
    console.error("Invalid exp_condition: " + exp_condition);
  }
};
