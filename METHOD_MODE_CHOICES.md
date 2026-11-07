# Cards: choices awaiting confirmation

Each function's card has a row per statement in it, flat, in the order
written. A statement that holds decisions is replaced by the outermost decisions
in it, each followed by the decisions inside it. The choices below are
provisional. Each one is pinned by the test named, in
test/test_method_statements.py unless stated.

## Rows

1. A docstring is not a row, since Python runs no code for it, in a
   function or a class. A constant other than a string, such as `...`,
   is a row: a value. (b47e3a01, b47e3a03, b47e3a22)

2. An if's arms, an elif's and an else's statements are rows after the
   if, an elif being a row of the else before it. A match's cases'
   statements are rows after the match, case by case. (b47e3a04,
   b47e3a23, b47e3a24)

3. A for loop is a row, `for`, or its header's decisions; a while loop's row
   is its test's decisions, or `while`. Then a row for each statement of the
   body and of the loop's else. (b47e3a11, b47e3a21)

4. A try is a row, `try`, then a row for each statement of its body, each
   handler, its else and its finally. A with is a row, `with`, or its
   items' decisions, then its body's rows. A class inside a function is a row,
   `class`, then its body's rows. (b47e3a12, b47e3a21)

5. A nested def is one row, `def`: its body runs only when it is called,
   and it has its own card. (b47e3a16)

6. A lambda's body and a comprehension's parts give a row for each decision in
   them, after the statement holding them, but no row of their own, as no
   reach call can sit inside an expression. (b47e3a11, b47e3a21)

7. A decision inside a decision's leaf, eg a ternary in a call inside an and, is
   a row of its own after the decision holding it. (b47e3a25)

8. A decision outside every function is a top row, on the card of its span of
   lines, titled by the innermost class holding it, or `file`. Each file's
   top rows are totalled as `path:0:0`, so every decision is in some total.
   (b47e3a27 to b47e3a29; test/test_listed_cards.py d3c9a101)

9. Every decision of this repo's src and test is a card row or a top row.
   (b47e3a30)

## Tops (the row's label)

10. A decision row is named by its operator: if, and, or, ternary, match,
    filter, any, all; an elif's is `elif`. It sits where its decision is
    named: an if or match at its keyword, a ternary at its own column.
    (b47e3a04, b47e3a05, b47e3a21, b47e3a23)

11. Any other row is named by its statement:

        for, while, with, try, def, class, raise, return
        =        Assign, AugAssign, AnnAssign
        ()       an expression statement that is a call
        value    anything else: assert, await, pass, a bare name, ...

    (b47e3a01, b47e3a02, b47e3a13, b47e3a19)

## Counting

12. A row that is not a decision is counted where its statement's first
    instruction runs, at every copy Python makes of it, an instruction
    event code_map marks with a Reach of its "path:line:col"; a function's
    entry where its code starts. No statement is added, so line traces are
    unchanged. (test/test_code_map.py 7b20d401, 7b20d40e,
    test/test_monitor.py d86a1f0c, d86a1f16)

13. Every run measures within each method; there is no measure setting.
    The JSON report's "reached" key is always written, even empty. When
    rendering, reached is summed across runs and parts. A run without it
    leaves its rows unknown, and an unknown row counts as not taken.
    (test/test_kernel.py e5a70c0b, e5a70c13, e5a70c14)

## HTML

14. Code is coloured by Python's tokenize: keywords, numbers, strings,
    comments, and names starting with a capital (as classes and constants
    do). Soft keywords, eg match and case, are left plain, as tokenize
    cannot tell them from names. (test/test_html_report.py 4f08d211,
    4f08d212)

15. The index's percent rounds a half up, 62.5% to 63%, not to the even
    62% Python's round gives. (test/test_html_report.py 4f08d205)
