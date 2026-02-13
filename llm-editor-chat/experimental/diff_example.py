import difflib

def show_diff_example():
    # Original text
    original = """Austria plans for war
Austria hoped Prussia would assist them in a war with France.
The negotiations were intercepted by French agents.
Stein fled into exile in Austria.""".splitlines(keepends=True)

    # Modified text
    modified = """Austria plans for war
Austria, seeking independence, hoped Prussia would join their fight against France.
The secret negotiations were discovered by Napoleon's agents.
Baron von Stein was forced to flee to Austria.""".splitlines(keepends=True)

    # Generate unified diff
    diff = list(difflib.unified_diff(
        original,
        modified,
        fromfile='original',
        tofile='modified',
        n=1  # Show 1 line of context
    ))
    
    print("1. Standard Unified Diff Format:")
    print(''.join(diff))
    
    print("\n2. Windsurf-style Format:")
    print("@@ Editing section: Austria plans for war @@")
    print("Current content:")
    for line in original:
        print(f"- {line}", end='')
    print("\nNew content:")
    for line in modified:
        print(f"+ {line}", end='')

if __name__ == "__main__":
    show_diff_example()
