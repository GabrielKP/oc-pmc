define(["component/Pages"], function (Pages) {
  let study;
  let page1and2;
  let page3;
  return {
    name: "general_instructions",
    init: function (_study) {
      study = _study;
      page1and2 = new Pages();
      page3 = new Pages();
      return Promise.all([
        page1and2.init(
          study,
          [
            "general_instructions/instruct-1.html",
            "general_instructions/instruct-2.html",
          ],
          function () {
            // show page 2 (need to reset in case this is not the first time)
            page3.reset();
            page3.next();
            // set study time
            $("#studytime_day2").text(study.config["studytime_day2"]);
            // bind previous button
            $("#prevC").on("click", () => {
              page1and2.reset();
              page1and2.next();
            });
          }
        ),
        page3.init(
          study,
          ["general_instructions/instruct-3.html"],
          function () {
            study.next();
          }
        ),
      ]);
    },
    show: function () {
      page1and2.next();
    },
  };
});
