define(["component/Pages"], function (Pages) {
  class _FreeAssociation {
    listening = false;
    word_count = 0;
    word_start_time;
    word_end_time;
    word_text;
    word_key_chars;
    word_key_codes;
    word_key_onsets;
    key_start_time;
    key_end_time;
    mode;
    pages;
    pagenames;
    finish_func;
    study;
    task_start_time;
    time_limit;

    constructor() {
      // bind all the functions
      this.response_handler = this.response_handler.bind(this);
      this.show_next = this.show_next.bind(this);
      this.show_next_exp_suppress = this.show_next_exp_suppress.bind(this);
      this.show_cue_new_textbox = this.show_cue_new_textbox.bind(this);
      this.save_word = this.save_word.bind(this);
      this.ready_word_variables = this.ready_word_variables.bind(this);
      this.fade_cue = this.fade_cue.bind(this);
      this.start_task = this.start_task.bind(this);
      this.finish_task = this.finish_task.bind(this);
    }

    init(study, pagename, finish_func, time_limit) {
      this.study = study;
      this.pages = new Pages();
      this.finish_func = finish_func;
      this.pagenames = [pagename];
      this.time_limit = time_limit;
      return this.pages.init(this.study, this.pagenames);
    }

    finish_task() {
      this.study.data.record_trialdata({
        status: "task_end",
        task: "free_association",
        task_time: new Date().getTime() - this.task_start_time,
      });
      $("body").unbind("keydown", this.response_handler);
      this.finish_func();
    }

    fade_cue(text, time_until_fade_out = 500, time_fade_out = 500) {
      $("#cue").html(text);
      $(".stim-div").fadeTo(250, 1);
      setTimeout(function () {
        $(".stim-div").fadeTo(time_fade_out, 0);
      }, time_until_fade_out);
    }

    save_word() {
      var submit_object = {};
      this.word_text = $("#qinput").val();
      submit_object["task"] = "free_association";
      submit_object["status"] = "data";
      submit_object["word_text"] = this.word_text;
      submit_object["word_count"] = this.word_count;
      submit_object["word_time"] = this.word_end_time - this.word_start_time;
      submit_object["word_key_chars"] = this.word_key_chars;
      submit_object["word_key_codes"] = this.word_key_codes;
      submit_object["word_key_onsets"] = this.word_key_onsets;
      this.study.data.record_trialdata(submit_object);
    }

    ready_word_variables() {
      this.word_key_chars = [];
      this.word_key_codes = [];
      this.word_key_onsets = [];
      this.word_start_time = new Date().getTime();
      this.key_start_time = new Date().getTime();
      this.listening = true;
    }

    show_cue_new_textbox() {
      $("#qinput").val("");
      this.fade_cue(this.word_text.toUpperCase());
      this.ready_word_variables();
    }

    /*****
     * This function switches to the appropriate next mode,
     * dependent on the previous mode. It will then initiate
     * the correct display of the next mode.
     */
    show_next() {
      this.show_next_exp_suppress();
    }

    show_next_exp_suppress() {
      if (this.mode == "end") {
        this.finish_task();
      } else {
        this.show_cue_new_textbox();
      }
    }

    response_handler(key) {
      if (!this.listening) return;
      this.listening = false;
      if (key.keyCode == 13) {
        // "ENTER" - key

        if ($("#qinput").val() == "") {
          // do not submit if textbox is empty
          this.listening = true;
          key.preventDefault();
          return;
        }

        // record keystroke
        this.key_end_time = new Date().getTime();
        this.word_key_chars.push(String.fromCharCode(key.keyCode));
        this.word_key_codes.push(key.keyCode);
        this.word_key_onsets.push(this.key_end_time - this.key_start_time);

        // Submit data to psiturk
        this.word_end_time = new Date().getTime();
        this.word_text = $("#qinput").val();
        this.save_word();
        this.word_count++;

        // disable enter key's default function (keeps text box unchanged after pressing enter)
        key.preventDefault();

        this.show_next();
      } else if (
        key.keyCode == 32 ||
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
        // DISABLED keys: space bar and many non-alphanumeric characters
        key.preventDefault();
        this.listening = true;
      } else {
        // "NORMAL" keys: save key char, code and time
        this.key_end_time = new Date().getTime();
        this.word_key_chars.push(String.fromCharCode(key.keyCode));
        this.word_key_codes.push(key.keyCode);
        this.word_key_onsets.push(this.key_end_time - this.key_start_time);
        this.key_start_time = new Date().getTime();
        this.listening = true;
      }
    }

    start_task() {
      // show the free association
      this.pages.next();

      // beginning of free association
      this.study.data.record_trialdata({
        status: "task_begin",
        task: "free_association",
      });
      this.task_start_time = new Date().getTime();

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
      $("body").focus().keydown(this.response_handler);

      $("#cue").html("Enter a word to begin!");
      // Timer for FA
      setTimeout(() => {
        this.mode = "end";
      }, this.time_limit);

      this.mode = "word_chain_game";
      this.ready_word_variables();
    }
  }

  return _FreeAssociation;
});
