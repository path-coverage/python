# Method mode: choices awaiting confirmation

In method mode, each function's card has one row per top-level statement
of its body. A statement that holds sites is replaced by the outermost
sites in it. The choices below are provisional. Each one is pinned by
the test named, in test/test_method_statements.py unless stated.

## Rows

1. A docstring is not a row, since Python runs no code for it.
   A constant other than a string, such as `...`, is a row: a value.
   (b47e3a01, b47e3a03, b47e3a22)

2. Some statements are not looked through, as their bodies run in a
   context of their own. Each one is a single row:
   def, async def, class, lambda, and list, set and dict comprehensions
   and generator expressions.

       def labels(items):
           names = ['sale' if i.sale else 'full' for i in items]

   The row is `=`, not the ternary. (b47e3a11, b47e3a16, b47e3a21)

3. For a for loop, only the header (its target and iterable) is looked
   through. For a while loop, only its test is. The body runs once per
   item, so an if inside it is not a row of the function.

       def tally(items):
           for item in items:
               if item.sale:
                   item.count()

   That is one row, `for`. (b47e3a11, b47e3a21)

4. A try is looked through in its body, its else and its finally. Its
   except handlers are not, since they run only on a raise. A try with
   no site outside its handlers is one row, `try`. (b47e3a12)

5. A with is looked through, so a site inside it is a row. (b47e3a21)

## Tops (the row's label)

6. A site row is named by its operator: if, and, or, ternary, match,
   any, all, and so on. It sits where decision mode places that site:
   an if or match at its keyword, a ternary at its own column.
   (b47e3a04, b47e3a05, b47e3a21)

7. Any other row is named by its statement:

       for, while, with, try, def, class, raise, return
       =        Assign, AugAssign, AnnAssign
       ()       an expression statement that is a call
       value    anything else: assert, await, pass, a bare name, ...

   (b47e3a01, b47e3a02, b47e3a13, b47e3a19)

## Counting

8. A row that is not a site is counted by a reach call. The rewriter
   inserts `__path_coverage__.reach("path:line:col")` as a statement
   just before it. The call is placed at that statement's start with
   no width, so line traces are unchanged. (test/test_rewriter.py
   7e40b305)

9. The JSON report's "reached" key is written whenever methods are
   measured, even when it is empty. It is absent otherwise. When
   rendering, reached is summed across runs and parts. A run without
   it leaves its rows unknown, and an unknown row counts as not taken.
   (test/test_kernel.py e5a70c13, e5a70c14)

## HTML

10. The card's title row has a title attribute,
    "name: N of M paths taken". side.js copies it into the function
    bar's tooltip. (test/test_html_statements.py c81d5f01)

11. Nothing in a card is escaped. Python names and tops hold no markup.

12. The page has no mode toggle. Clicking a site row opens the tree
    of the block that holds that line. This is unchecked in a browser.

## Still open

- The README still describes method paths (the sections Within each
  method, What a run reports, Methods, Reporters and How it works).
  Its rewrite needs your wording.
