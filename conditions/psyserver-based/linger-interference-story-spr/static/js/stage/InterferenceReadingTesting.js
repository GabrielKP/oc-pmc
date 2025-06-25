define(["component/Pages", "component/InterferenceReading"], function (
  Pages,
  InterferenceReading
) {
  let study;
  let task_pages;
  let task;

  function _init_start_task() {
    task_pages.reset();
    task = new InterferenceReading();
    task.init(
      study,
      task_pages,
      () => {
        study.next();
      },
      false,
      study.config["interference_reading_delay_key"]
    );
    task.start_task();
  }

  return {
    name: "interference_reading_testing",
    init: function (_study) {
      study = _study;
      task_pages = new Pages();
      return Promise.all([
        task_pages.init(study, "interference_reading_testing/task.html"),
      ]);
    },
    show: function () {
      _init_start_task();
    },
    finish_task: function (skip = false) {
      task.finish_task(skip);
    },
  };
});
