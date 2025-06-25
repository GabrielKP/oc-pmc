define(function () {
  // Class for page handling
  class _Pages {
    page_index;
    pages;
    pagenames;
    func_finish;
    study;

    constructor() {
      this.next = this.next.bind(this);
      this.previous = this.previous.bind(this);
      this.current_page_name = this.current_page_name.bind(this);
      this._display_page = this._display_page.bind(this);
      this._page_end = this._page_end.bind(this);
    }

    init(study, pagenames, func_finish = null) {
      this.study = study;
      this.page_index = -1;

      if (pagenames.constructor !== Array) {
        pagenames = [pagenames];
      }
      this.pages = Array(pagenames.length);
      this.func_finish = func_finish;
      this.pagenames = pagenames;

      this._page_time_start = null;

      return Promise.all(
        $.map(pagenames, (pagename, indx) => {
          return $.ajax({
            url: pagename,
            dataType: "html",
          }).then((page_html) => {
            console.debug("Page loaded: " + indx + " " + pagename);
            this.pages[indx] = page_html;
          });
        })
      );
    }

    _bind_buttons(func_next, func_previous) {
      $("#next").on("click", function () {
        func_next();
      });
      $("#prev").on("click", function () {
        func_previous();
      });
    }

    _enable_buttons(button_timeout) {
      setTimeout(function () {
        $("#next").prop("disabled", false);
      }, button_timeout);
      $("#prev").prop("disabled", false);
    }

    _display_page(button_timeout = 0) {
      // display page
      $("#content").html(this.pages[this.page_index]);
      // set timer
      this._page_time_start = new Date().getTime();
      // bind button functions
      this._bind_buttons(this.next, this.previous);
      this._enable_buttons(button_timeout);
    }

    _page_end(action) {
      this.study.data.record_trialdata({
        page: this.current_page_name(),
        action: action,
        page_time: new Date().getTime() - this._page_time_start,
      });
    }

    next() {
      if (this.page_index < this.pages.length - 1) {
        // only record page after first page
        if (this.page_index >= 0) {
          this._page_end("pages_next");
        }
        this.page_index += 1;
        this._display_page(this.study.config.default_button_timeout);
        return true;
      } else {
        if (this.func_finish != null) {
          this._page_end("pages_next");
          this.func_finish();
        } else {
          console.warn("No next page & no func_finish.");
        }
        return false;
      }
    }

    previous() {
      if (this.page_index > 0) {
        this._page_end("pages_previous");

        // display previous
        this.page_index -= 1;
        this._display_page(0);

        return true;
      } else {
        console.log("No previous page");
        return false;
      }
    }

    current_page_name() {
      if (this.page_index == -1) {
        return "no_page";
      }
      return this.pagenames[this.page_index];
    }

    reset() {
      this.page_index = -1;
    }
  }

  return _Pages;
});
