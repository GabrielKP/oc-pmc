define(["component/TomPassages", "component/TomQuestions"], function (
  TomPassages,
  TomQuestions
) {
  class _InterferenceTom {
    total_pause_time;
    mode;
    pages;
    pagenames;
    passage_indices;
    finish_func;
    study;
    task_start_time;
    initial_press;
    iteration;
    time_passage;
    time_question;
    time_isi;
    failed_passage;
    failed_question;
    listening;
    mode_start_time;
    answered_passage1;
    answered_passage2;
    answered_question1;
    answered_question2;
    timeout_handler;

    constructor() {
      // bind all the functions
      this.keydown_handler = this.keydown_handler.bind(this);
      this.switch_mode = this.switch_mode.bind(this);
      this.finish_task = this.finish_task.bind(this);
      this.start_task = this.start_task.bind(this);
      this.button_handler = this.button_handler.bind(this);
      this.record_button_press = this.record_button_press.bind(this);
      this.record_keydown = this.record_keydown.bind(this);
    }

    init(
      study,
      page_object,
      finish_func,
      passage_indices,
      time_passage,
      time_question,
      time_pause,
      iteration = 0
    ) {
      this.study = study;
      this.pages = page_object;
      this.finish_func = finish_func;
      this.passage_indices = passage_indices;
      this.current_time = 0;
      this.iteration = iteration;
      this.initial_press = true;
      this.time_passage = time_passage;
      this.time_question = time_question;
      this.time_pause = time_pause;
      this.tom_passages = TomPassages;
      this.tom_questions = TomQuestions;
      this.mode = "init"; // init | passage | question | pause
      this.listening = false;
      this.answered_passage = false;
      this.answered_question = false;
    }

    finish_task(skip = false) {
      // unbind
      $("body").off();

      // record data
      let task_time = new Date().getTime() - this.task_start_time;
      this.study.data.record_trialdata({
        status: "task_end",
        task: "interference_tom",
        iteration: this.iteration,
        task_time: task_time,
      });
      // $("body").unbind("keydown", this.response_handler);
      $("body").css({ border: "", height: "" });
      $("html").css({ height: "" });
      if (!skip)
        this.finish_func(this.answered_question, this.answered_passage);
      else {
        clearTimeout(this.timeout_handler);
        this.study.next();
      }
    }

    record_keydown(pressed) {
      let passage_index = this.passage_indices[this.iteration];
      this.study.data.record_trialdata({
        status: "ongoing",
        task: "interference_tom",
        iteration: this.iteration,
        mode: this.mode,
        read_time: new Date().getTime() - this.mode_start_time,
        passage: this.tom_passages[passage_index],
        passage_index: passage_index,
        pressed: pressed,
      });
    }

    keydown_handler(key) {
      key.preventDefault();

      if (!this.listening || !this.mode == "passage") return;
      this.listening = false;

      // ignore everything but enter key
      if (key.keyCode != 13) {
        this.listening = true;
        return;
      }

      // track success
      this.answered_passage = true;

      // record press
      this.record_keydown(true);

      // visual feedback
      $("#pressed-indicator").css("opacity", 100);
    }

    record_button_press(answer) {
      let question_index = this.passage_indices[this.iteration];
      this.study.data.record_trialdata({
        status: "ongoing",
        task: "interference_tom",
        iteration: this.iteration,
        mode: this.mode,
        answer_time: new Date().getTime() - this.mode_start_time,
        passage: this.tom_passages[this.passage_indices[this.iteration]],
        question_index: question_index,
        answer: answer,
      });
    }

    button_handler(answer) {
      if (!this.listening || !this.mode == "question") return;
      this.listening = false;

      // track success
      this.answered_question = true;

      $("#yes").addClass("disabled");
      $("#no").addClass("disabled");

      this.record_button_press(answer);
    }

    switch_mode() {
      // hide/show the correct things, and set appropriate timers
      switch (this.mode) {
        case "init":
          this.mode = "passage";
          this.timeout_handler = setTimeout(() => {
            this.switch_mode();
          }, this.time_passage);

          $("#container-passage").show();
          $("#text-passage").html(
            this.tom_passages[this.passage_indices[this.iteration]]
          );
          break;

        case "passage":
          if (!this.answered_passage) this.record_keydown(false);
          this.mode = "question";
          this.timeout_handler = setTimeout(() => {
            this.switch_mode();
          }, this.time_question);

          $("#container-passage").hide();
          $("#container-question").show();
          $("#text-question").html(
            this.tom_questions[this.passage_indices[this.iteration]]
          );
          break;

        case "question":
          if (!this.answered_question) this.record_button_press("no_answer");
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

      // show blue border
      $("body").css({ border: "40px solid #CBC3E3", height: "100%" });
      $("html").css({ height: "100%" });

      // register event listener
      $("body").focus().keydown(this.keydown_handler);
      $("#yes").on("click", () => {
        this.button_handler("yes");
      });
      $("#no").on("click", () => {
        this.button_handler("no");
      });

      // kick off on screen action
      this.switch_mode();

      // log beginning of task
      this.study.data.record_trialdata({
        status: "task_begin",
        task: "interference_tom",
        iteration: this.iteration,
      });
      this.task_start_time = new Date().getTime();
    }
  }

  return _InterferenceTom;
});
