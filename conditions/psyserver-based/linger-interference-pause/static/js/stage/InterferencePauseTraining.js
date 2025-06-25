define(["component/Pages", "component/InterferencePause"], function (
  Pages,
  InterferencePause
) {
  let study;
  let instruct_5s_pages;
  let instruct_30s_pages;
  let step;
  let task_pages;
  let task;
  let iteration;

  function _init_start_task(pause_time) {
    task_pages.reset();
    task = new InterferencePause();
    task.init(
      study,
      task_pages,
      function (time_unpressed) {
        _conditional_next(time_unpressed);
      },
      pause_time,
      iteration
    );
    task.start_task();
  }

  function _conditional_next(time_unpressed) {
    if (step == "5s") {
      if (time_unpressed >= 1000) {
        iteration += 1;
        try_again_5s_pages.next();
      } else {
        instruct_30s_pages.next();
      }
    } else {
      if (time_unpressed >= 1500) {
        iteration += 1;
        try_again_30s_pages.next();
      } else {
        final_pages.next();
      }
    }
  }

  return {
    name: "interference_pause_training",
    init: function (_study) {
      study = _study;
      instruct_5s_pages = new Pages();
      task_pages = new Pages();
      try_again_5s_pages = new Pages();
      try_again_30s_pages = new Pages();
      instruct_30s_pages = new Pages();
      final_pages = new Pages();
      iteration = 0;
      step = "5s";
      return Promise.all([
        instruct_5s_pages.init(
          study,
          "interference_pause_training/instruct-5s.html",
          () => {
            _init_start_task(study.config["interference_pause_time_training"]);
          }
        ),
        instruct_30s_pages.init(
          study,
          "interference_pause_training/instruct-30s.html",
          () => {
            step = "30s";
            _init_start_task(study.config["interference_pause_time"]);
          }
        ),
        try_again_5s_pages.init(
          study,
          "interference_pause_training/instruct-try_again_5s.html",
          () => {
            _init_start_task(study.config["interference_pause_time_training"]);
          }
        ),
        try_again_30s_pages.init(
          study,
          "interference_pause_training/instruct-try_again_30s.html",
          () => {
            _init_start_task(study.config["interference_pause_time"]);
          }
        ),
        task_pages.init(study, "interference_pause_training/task.html"),
        final_pages.init(
          study,
          "interference_pause_training/instruct-final.html",
          function () {
            study.next();
          }
        ),
      ]);
    },
    show: function () {
      // show instructions first
      instruct_5s_pages.next();
    },
    finish_task: function () {
      task.finish_task();
    },
  };
});
