import argparse
import sys

from .cache import get_cache_stats, clear_cache
from .tracker import get_usage_stats, get_total_savings


def format_dollar(amount: float) -> str:
    if amount < 0.01:
        return f"{amount:.4f}"
    return f"{amount:.2f}"


def main():
    parser = argparse.ArgumentParser(
        description="Claude Saver — Track and manage your Claude API savings"
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    sub.add_parser("stats", help="Show usage and savings statistics")
    sub.add_parser("cache-stats", help="Show cache statistics")
    sub.add_parser("clear-cache", help="Clear all cached responses")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "stats":
        days = 30
        stats = get_usage_stats(days)
        total_savings = get_total_savings()

        print("=" * 50)
        print(f"  Claude Saver — Usage Report (last {days} days)")
        print("=" * 50)
        print(f"  Total requests:    {stats['total_requests']}")
        print(f"  Total cost:        ${format_dollar(stats['total_cost'])}")
        print(f"  Total saved:       ${format_dollar(stats['total_saved'])}")
        print(f"  Savings rate:      {stats['savings_rate']}%")
        print(f"  Prompt tokens:     {stats['total_prompt_tokens']:,}")
        print(f"  Completion tokens: {stats['total_completion_tokens']:,}")
        print(f"  Cached tokens:     {stats['total_cached_tokens']:,}")
        print()

        if stats["daily"]:
            print("  Daily breakdown:")
            print(f"  {'Date':<14} {'Cost':>8} {'Saved':>8} {'Requests':>10}")
            print(f"  {'-'*14} {'-'*8} {'-'*8} {'-'*10}")
            for d in stats["daily"][:14]:
                cost = format_dollar(d["cost"])
                saved = format_dollar(d["saved"])
                print(
                    f"  {d['date']:<14} ${cost:>6} ${saved:>6} {d['requests']:>10}"
                )
            print()

        if stats["model_breakdown"]:
            print("  By model:")
            print(f"  {'Model':<35} {'Requests':>10} {'Cost':>10} {'Saved':>10}")
            print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*10}")
            for m in stats["model_breakdown"]:
                cost = format_dollar(m["cost"])
                saved = format_dollar(m["saved"])
                print(
                    f"  {m['model']:<35} {m['requests']:>10} ${cost:>8} ${saved:>8}"
                )
            print()

        print(f"  Lifetime savings:  ${format_dollar(total_savings)}")
        print("=" * 50)

    elif args.command == "cache-stats":
        cs = get_cache_stats()
        print("=" * 40)
        print("  Claude Saver — Cache Statistics")
        print("=" * 40)
        print(f"  Cached responses:  {cs['total_cached']}")
        print(f"  Total cache hits:  {cs['total_hits']}")
        print(f"  Tokens saved:      {cs['total_tokens_saved']:,}")
        print(f"  Oldest entry:      {cs['oldest_entry'] or 'N/A'}")
        print(f"  Newest entry:      {cs['newest_entry'] or 'N/A'}")
        print("=" * 40)

    elif args.command == "clear-cache":
        confirm = input("Clear all cached responses? This cannot be undone. [y/N]: ")
        if confirm.lower() == "y":
            clear_cache()
            print("Cache cleared.")
        else:
            print("Aborted.")


if __name__ == "__main__":
    main()
