define(["component/InterferenceStoryTesting"], function (
  InterferenceStoryTesting
) {
  class _InterferenceReading {
    study;
    pages;
    story;
    sentence_index;
    sentence_start_time;
    task_start_time;
    reading_delay_key;
    finish_func;
    training;

    constructor() {
      // bind all the functions
      this.init.bind(this);
      this.finish_task.bind(this);
      this.show_story_sentence.bind(this);
      this.show_next.bind(this);
      this.response_handler.bind(this);
    }

    init(study, page_object, finish_func, training, reading_delay_key) {
      this.study = study;
      this.pages = page_object;
      this.finish_func = finish_func;
      this.sentence_index = 0;
      this.training = training;
      this.reading_delay_key = reading_delay_key;
      this.listening = false;
      if (this.training) this.story = InterferenceStoryTraining;
      else this.story = InterferenceStoryTesting;
    }

    finish_task(skip = false) {
      // unbind
      $("body").off();

      // record data
      this.study.data.record_trialdata({
        status: "task_end",
        task: "interference_reading",
        task_time: new Date().getTime() - this.task_start_time,
      });

      $("body").css({ border: "", height: "" });
      $("html").css({ height: "" });
      if (!skip) this.finish_func();
      else this.study.next();
    }

    show_story_sentence() {
      let sentence_text = this.story.row[this.sentence_index].Story;
      this.sentence_index++;
      $("#sentence").html(sentence_text);
      this.sentence_start_time = new Date().getTime();
      setTimeout(() => {
        this.listening = true;
      }, this.reading_delay_key);
    }

    show_next() {
      if (this.sentence_index == this.story.row.length) {
        this.finish_task();
      } else {
        this.show_story_sentence();
      }
    }

    response_handler(key) {
      key.preventDefault();
      if (!this.listening) return;
      this.listening = false;

      // ignore everything but enter key
      if (key.keyCode != 13) {
        this.listening = true;
        return;
      }

      let sentence_end_time = new Date().getTime();
      let sentence_text = $("#sentence").html();

      let submit_object = {};
      submit_object["task"] = "interference_reading";
      submit_object["status"] = "ongoing";
      submit_object["sentence_text"] = sentence_text;
      submit_object["sentence_time"] =
        sentence_end_time - this.sentence_start_time;
      submit_object["sentence_length"] = sentence_text.length;
      submit_object["sentence_index"] = this.sentence_index - 1;
      this.study.data.record_trialdata(submit_object);

      this.show_next();
    }

    start_task() {
      // show task
      this.pages.next();

      // show border
      $("body").css({ border: "40px solid #CBC3E3", height: "100%" });
      $("html").css({ height: "100%" });
      $("#sentence").css({ color: "purple" });

      // log beginning of task
      this.study.data.record_trialdata({
        status: "task_begin",
        task: "interference_reading",
      });
      this.task_start_time = new Date().getTime();

      // register event listener
      $("body").bind("keydown", (key) => {
        this.response_handler(key);
      });

      // kick off on screen action
      this.show_story_sentence();
    }
  }

  return _InterferenceReading;
});
