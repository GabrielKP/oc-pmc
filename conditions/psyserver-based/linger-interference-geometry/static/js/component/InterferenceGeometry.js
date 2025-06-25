define(function () {
  class _InterferenceGeometry {
    total_pause_time;
    mode;
    pages;
    pagenames;
    image_index;
    image_solutions;
    finish_func;
    study;
    task_start_time;
    initial_press;
    iteration;
    time_image;
    time_question;
    listening;
    answered_question;
    mode_start_time;
    timeout_handler;
    answered_correct;

    constructor() {
      // bind all the functions
      this.switch_mode = this.switch_mode.bind(this);
      this.finish_task = this.finish_task.bind(this);
      this.start_task = this.start_task.bind(this);
      this.button_handler = this.button_handler.bind(this);
      this.record_button_press = this.record_button_press.bind(this);
    }

    init(
      study,
      page_object,
      finish_func,
      image_index,
      time_image,
      time_question,
      time_pause,
      iteration
    ) {
      this.study = study;
      this.pages = page_object;
      this.finish_func = finish_func;
      this.image_index = image_index;
      //   indices:          [0,   1, 2,  3,  4, 5, 6, 7, 8,  9,10, 11,12,13]
      this.image_solutions = [-1, 11, 7, 10, 12, 4, 9, 5, 6, 13, 8, 14, 6, 9];
      this.current_time = 0;
      this.iteration = iteration;
      this.initial_press = true;
      this.time_image = time_image;
      this.time_question = time_question;
      this.time_pause = time_pause;
      this.mode = "init"; // init | image | question | pause
      this.listening = false;
      this.answered_question = false;
      this.correct_answer = this.image_solutions[this.image_index];
    }

    finish_task(skip = false) {
      // unbind
      $("body").off();

      // record data
      let task_time = new Date().getTime() - this.task_start_time;
      this.study.data.record_trialdata({
        status: "task_end",
        task: "interference_geometry",
        iteration: this.iteration,
        task_time: task_time,
      });
      // $("body").unbind("keydown", this.response_handler);
      $("body").css({ border: "", height: "" });
      $("html").css({ height: "" });
      if (!skip) this.finish_func(this.answered_correct, this.correct_answer);
      else {
        clearTimeout(this.timeout_handler);
      }
    }

    record_button_press(answer, answered_correct, correct_answer) {
      let image_id = "triangles-" + this.image_index;
      this.study.data.record_trialdata({
        status: "ongoing",
        task: "interference_geometry",
        iteration: this.iteration,
        mode: this.mode,
        answer_time: new Date().getTime() - this.mode_start_time,
        image_index: this.image_index,
        image_id: image_id,
        answer: answer,
        correct_answer: correct_answer,
        answered_correct: answered_correct,
      });
    }

    button_handler() {
      if (!this.listening || !this.mode == "question") return;
      this.listening = false;

      // track success
      this.answered_question = true;

      // disable input
      $("#submit").addClass("disabled");
      $("#answer-triangles").attr("disabled", true);

      // read textarea
      let answer = $("#answer-triangles").val();
      this.answered_correct = answer == this.correct_answer;

      this.record_button_press(
        answer,
        this.answered_correct,
        this.correct_answer
      );
    }

    switch_mode() {
      // hide/show the correct things, and set appropriate timers
      let image_div_id = "#triangles-" + this.image_index;
      switch (this.mode) {
        case "init":
          this.mode = "image";
          this.timeout_handler = setTimeout(() => {
            this.switch_mode();
          }, this.time_image);

          $("#container-image").show();
          $(image_div_id).show();
          break;

        case "image":
          this.mode = "question";
          this.timeout_handler = setTimeout(() => {
            this.switch_mode();
          }, this.time_question);

          $("#container-image").hide();
          $(image_div_id).hide();
          $("#container-question").show();
          break;

        case "question":
          if (!this.answered_question)
            this.record_button_press("no_answer", false, this.correct_answer);
          this.mode = "pause";
          this.timeout_handler = setTimeout(() => {
            this.switch_mode();
          }, this.time_pause);

          $("#container-question").hide();
          break;

        case "pause":
          this.finish_task();
          break;
      }
      this.mode_start_time = new Date().getTime();
      this.listening = true;
    }

    start_task() {
      // show task
      this.pages.next();

      // show purple border
      $("body").css({ border: "40px solid #CBC3E3", height: "100%" });
      $("html").css({ height: "100%" });

      // register event listener
      $("#submit").on("click", () => {
        this.button_handler();
      });

      // kick off on screen action
      this.switch_mode();

      // log beginning of task
      this.study.data.record_trialdata({
        status: "task_begin",
        task: "interference_geometry",
        iteration: this.iteration,
      });
      this.task_start_time = new Date().getTime();
    }
  }

  return _InterferenceGeometry;
});
