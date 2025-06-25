define(["component/Pages", "component/DarkBedroom"], function (Pages, Story) {
  let study;
  let instruct_pages;
  let reading_pages;
  // Reading Task variables
  let story;
  let listening = false;
  let sentence_index = 0;
  let sentence_text;
  let sentence_start_time;
  let sentence_end_time;
  let task_start_time;
  let reading_delay_key;

  function _finish_task() {
    $("body").unbind("keydown", response_handler);
    study.data.record_trialdata({
      status: "task_end",
      task: "reading",
      task_time: new Date().getTime() - task_start_time,
    });
    study.next();
  }

  function show_story_sentence() {
    sentence_text = story.row[sentence_index].Story;
    sentence_index++;
    $("#sentence").html(sentence_text);
    sentence_start_time = new Date().getTime();
    setTimeout(function () {
      listening = true;
    }, reading_delay_key);
  }

  function show_next() {
    if (sentence_index == story.row.length) {
      _finish_task();
    } else {
      show_story_sentence();
    }
  }

  function response_handler(key) {
    key.preventDefault();
    if (!listening) return;
    listening = false;

    // ignore everything but enter key
    if (key.keyCode != 13) {
      listening = true;
      return;
    }

    sentence_end_time = new Date().getTime();
    sentence_text = $("#sentence").html();

    let submit_object = {};
    submit_object["task"] = "reading";
    submit_object["status"] = "ongoing";
    submit_object["sentence_text"] = sentence_text;
    submit_object["sentence_time"] = sentence_end_time - sentence_start_time;
    submit_object["sentence_length"] = sentence_text.length;
    submit_object["sentence_index"] = sentence_index - 1;
    study.data.record_trialdata(submit_object);

    show_next();
  }

  function start_reading() {
    // show reading page
    reading_pages.next();

    // record beginning
    study.data.record_trialdata({
      status: "task_begin",
      task: "reading",
    });
    task_start_time = new Date().getTime();

    // register event listener
    $("body").bind("keydown", response_handler);

    //enable
    show_story_sentence();
    listening = true;
  }

  return {
    name: "reading",
    init: function (_study) {
      study = _study;
      instruct_pages = new Pages();
      reading_pages = new Pages();
      story = Story;
      reading_delay_key = study.config.reading_delay_key;
      return Promise.all([
        instruct_pages.init(
          study,
          ["reading/instruct-1.html", "reading/instruct-2.html"],
          function () {
            start_reading();
          }
        ),
        reading_pages.init(study, "reading/task.html"),
      ]);
    },
    show: function () {
      // show instructions first
      instruct_pages.next();
    },
    finish_task: function () {
      _finish_task();
    },
  };
});
