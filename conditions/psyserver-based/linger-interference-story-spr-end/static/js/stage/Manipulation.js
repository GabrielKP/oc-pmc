define(["component/Pages", "component/InterferenceGeometry"], function (
  Pages,
  InterferenceGeometry
) {
  let study;

  let continued_pages;
  let separated_pages;
  let delayed_continued_1;
  let delayed_continued_2;

  let task_pages;
  let intask;
  let iteration;
  let image_indices;

  let task;

  function _init_start_task(iteration) {
    task_pages.reset();
    task = new InterferenceGeometry();
    task.init(
      study,
      task_pages,
      () => {
        _conditional_next();
      },
      image_indices[iteration],
      study.config["interference_geometry_time_image"],
      study.config["interference_geometry_time_question"],
      study.config["interference_geometry_time_pause"],
      iteration
    );
    task.start_task();
  }

  function _conditional_next() {
    if (iteration < image_indices.length) {
      _init_start_task(iteration);
      iteration++;
    } else {
      intask = false;
      delayed_continued_2.next();
    }
  }

  return {
    name: "manipulation",
    init: function (_study) {
      study = _study;

      // Pages setup
      continued_pages = new Pages();
      separated_pages = new Pages();
      delayed_continued_1 = new Pages();
      delayed_continued_2 = new Pages();

      // Geometry task setup
      task_pages = new Pages();
      intask = false;
      iteration = 0;
      image_indices =
        study.config["interference_geometry_testing_image_indices"];

      // Pages pre-loading
      return Promise.all([
        continued_pages.init(
          study,
          ["manipulation/continued.html"],
          function () {
            study.next();
          }
        ),
        separated_pages.init(
          study,
          ["manipulation/separated.html"],
          function () {
            study.next();
          }
        ),
        delayed_continued_1.init(
          study,
          ["manipulation/delayed_continued_1.html"],
          function () {
            intask = true;
            _conditional_next();
          }
        ),
        delayed_continued_2.init(
          study,
          ["manipulation/delayed_continued_2.html"],
          function () {
            study.next();
          }
        ),
        task_pages.init(study, "interference_geometry_testing/task.html"),
      ]);
    },
    show: function () {
      switch (study.config["condition"]) {
        case "continued":
          continued_pages.next();
          break;

        case "separated":
          separated_pages.next();
          break;

        case "delayed-continued":
          delayed_continued_1.next();
          break;
      }
    },
    finish_task: function (skip = false) {
      if (intask) task.finish_task(skip);
      else study.next();
    },
  };
});
