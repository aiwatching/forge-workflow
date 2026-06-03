# Mantis Advance Search — Boolean Syntax Reference

> Full reference for the `filter_query` input on `fortinet-mantis-bug-fix-batch`.
> The pipeline forwards the query verbatim to Mantis's `search=` URL parameter, which runs against **bug summary + description + additional info + bug notes** when full-text search is enabled (`$g_use_full_text_search = ON`).

## Boolean Operators

| Operator | Meaning | Example |
|---|---|---|
| `+` | word must be present (AND) | `+apple +juice` |
| `-` | word must NOT be present | `+apple -macintosh` |
| `\|` | OR | `apple \| banana` |
| `(` `)` | precedence | `+(apple banana) -juice` |
| `*` | wildcard | `apple*` → apple, apples, applet |
| `" "` | exact phrase | `"some words"` |

## Common Gotchas (read before writing queries)

### 1. Stopwords are silently dropped (unless in a phrase)
Common English words ("no", "applied", "the", "this", "have", "be", "is", …) are stripped before matching. Standalone `-no` does nothing.

✅ **Workaround**: wrap stopword phrases in quotes — phrase mode keeps every word.

```
BAD:  -no fix applied            → actually parses as -fix (and -fix may also trip rule 3)
GOOD: -"no fix applied"          → exact phrase match, stopwords preserved
```

### 2. Hyphenated words are split
Mantis treats `-` inside a token as a word separator. `-Auto-fix` parses as `NOT Auto, NOT fix`, not `NOT "Auto-fix"`.

✅ Quote it: `-"Auto-fix"`.

### 3. The 50% rule
If a word appears in more than half of the indexed rows, it is treated as a stopword and ignored. Common project-specific words ("fix", "bug", "release") can silently drop out.

✅ Use a **phrase** (`-"fix this"`) instead of a bare word — phrase mode bypasses the 50% rule.

### 4. Minimum word length
Words shorter than 2 characters are skipped.

## Ready-to-use Templates

| Goal | Query |
|---|---|
| Skip bugs Forge already touched | `-"no fix applied" -"Auto-fix" -forge` |
| Only authentication-related, exclude OAuth | `+auth -oauth` |
| Either crash OR hang, not in 7.4 | `(crash \| hang) -"7.4"` |
| Wildcard prefix match | `authent*` |

## Where to Test

Before relying on a query in the pipeline, paste it into the Advanced Search box on Mantis's `view_all_bug_page.php`. The same string runs there.

## Authoritative Reference

This document is a working subset. The canonical Mantis behaviour matches MySQL InnoDB FULLTEXT `IN BOOLEAN MODE`. Full stopword list and edge-case rules: see your Mantis admin's Advance Search help page (linked from the Advanced Search button).
