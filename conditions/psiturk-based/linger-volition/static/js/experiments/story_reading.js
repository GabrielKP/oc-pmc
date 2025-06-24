/***********************************
 * Story reading *
 ***********************************/

var StoryReading = function () {
  var listening = false;
  var sentence_index = 0;
  var sentence_text;
  var sentence_start_time;
  var sentence_end_time;

  function finish_task() {
    $("body").unbind("keydown", response_handler);
    psiTurk.recordTrialData({ phase: "story_reading", status: "end" });
    finish_story_reading();
  }

  function show_story_sentence() {
    sentence_text = story.row[sentence_index].Story;
    sentence_index++;
    $("#sentence").html(sentence_text);
    sentence_start_time = new Date().getTime();
    setTimeout(function () {
      listening = true;
    }, SPR_DELAY_KEY_ACTIVE);
  }

  function show_next() {
    if (sentence_index == story.row.length) {
      finish_task();
    } else {
      show_story_sentence();
    }
  }

  function response_handler(key) {
    if (!listening) return;
    listening = false;
    key.preventDefault();

    // ignore everything but enter key
    if (key.keyCode != 13) {
      listening = true;
      return;
    }

    sentence_end_time = new Date().getTime();
    sentence_text = $("#sentence").html();

    var submit_object = {};
    submit_object["phase"] = "story_reading";
    submit_object["status"] = "ongoing";
    submit_object["sentence_text"] = sentence_text;
    submit_object["sentence_time"] = sentence_end_time - sentence_start_time;
    submit_object["sentence_length"] = sentence_text.length;
    psiTurk.recordTrialData(submit_object);

    show_next();
  }

  // load initial display
  psiTurk.showPage("story_reading.html");
  psiTurk.recordTrialData({ phase: "story_reading", status: "begin" });

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

  // start showing sentences
  show_story_sentence();
};
