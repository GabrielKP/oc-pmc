define(["component/Pages", "component/InterferenceReading"], function (
  Pages,
  InterferenceReading
) {
  let study;
  let instruct_pages;
  let task_pages;
  let task;
  let mode;

  function _init_start_task() {
    mode = "task";
    task_pages.reset();
    task = new InterferenceReading();
    task.init(
      study,
      task_pages,
      () => {
        next();
      },
      true,
      study.config["interference_reading_delay_key"]
    );
    task.start_task();
  }

  function next() {
    if (mode == "init") {
      mode = "instructions";
      instruct_pages.next();
    } else if (mode == "instructions") {
      _init_start_task();
    } else if (mode == "task") {
      final_pages.next();
    }
  }

  return {
    name: "interference_reading_training",
    init: function (_study) {
      study = _study;
      instruct_pages = new Pages();
      task_pages = new Pages();
      final_pages = new Pages();
      mode = "init";
      return Promise.all([
        instruct_pages.init(
          study,
          [
            "interference_reading_training/instruct-1.html",
            "interference_reading_training/instruct-2.html",
            "interference_reading_training/instruct-3.html",
          ],
          () => {
            _init_start_task();
          }
        ),
        task_pages.init(study, "interference_reading_training/task.html"),
        final_pages.init(
          study,
          "interference_reading_training/instruct-final.html",
          function () {
            study.next();
          }
        ),
      ]);
    },
    show: function () {
      next();
    },
    finish_task: function (skip = false) {
      if (mode == "instructions") {
        _init_start_task();
      } else if (mode == "task") {
        task.finish_task(skip);
        study.next();
      } else {
        study.next();
      }
    },
  };
});
