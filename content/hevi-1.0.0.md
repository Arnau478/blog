---
{
    .title = "Introducing hevi: a hex viewer",
    .date = @date("2024-07-04"),
    .author = "Arnau Camprubí",
    .draft = false,
    .layout = "post.html",
    .tags = ["zig"],
}
---

Almost a year ago, I started writing *hevi*. Today, hevi 1.0.0 was released. Following the release, I decided I would write a blog post about it. I'll address the following:
- Why do we need *another* tool like `xxd` or `hexdump`?
- What makes a tool good?
- Why is `hevi` the best tool available?

# Why another tool

`xxd`, `hexdump`, `hexyl`... There's a lot of tools like `hevi` out there. However, I feel like none of them is good *enough*. Most of them either are really old pieces of software or don't offer many essential features.

For instance, `xxd` (bundled with `vim`) and `hexdump` are really old and primitive tools. Sure, they get the job done most of the times, but they're not pleasant to use by any means (obscure flags, long manpages...). `hexyl` on the other hand is a modern hex viewer... that offers little to no features.

I won't talk about GUI tools, as I think those are in a completely different context.

Bringing a new tool to the ecosystem is often viewed as a bad idea. But when all the other alternatives don't cut it, creating a new one *does* make sense.

# What makes a tool good?

We've just decided that we need a new hex viewer. What do we do now? Start writing a tool that will be as bad as the ones that are already out there? No. We think frist.

## Semantic flags
For a CLI program, the main way the user will interact with it is, well, the CLI. If a program has obscure flags that the user has to remember, it can be very harmful to the entire experiece. `hevi` does not have single-character flags. The only exceptions are `-h` and `-v`, which are well-known and widespread (but even those have semantic alternatives, `--help` and `--version`).

Sure, we could add shorthards for certain flags (e.g. `-c` for `--color`), but that would only encourage bad habits. By not having those, we push users towards a more semantic usage.

If your program needs to have single-character flags in order to provide a concise and short CLI usage, maybe you've got another problem...

## Defaults
I like the ASCII interpretation of the bytes. But some people don't. Do all those people have to type `--no-ascii` every single time they want to use the tool? Of course not. We want to create a versatile tool, that can suit the needs of as much users as possible. Having a way to override the defaults is the way to go.

`hevi` archives this by allowing the user to create a config file. In it, the user can decide if they want to have ASCII or not *by default*. They can still use `--ascii` and `--no-ascii`, but it will default to what the user likes, not to what the developer wants.

Having config files doesn't seem like a big deal, but many programs do it in a very bad way, having little to no connection to the flags.

## Diagnostics
If the user has an invalid config or passes an invalid flag, we need to report it properly. We shouldn't say "error: invalid config" and exit. Having good diagnostics, specially for the config file, is an essential piece that makes for a good tool.

## Features the user wants
Ideally, the tool should support every single feature the user wants, but not many unwanted ones. We don't want the user to feel like the tool is bloated.

For example, if you're dumping the contents of an ELF file, you're probably interested in its structure. `hevi` can parse ELF files and give the user a syntax-highlighted dump. It is an optional feature, and does not affect the executable size significantly.

## Modularity
A tool as generic as a hex viewer should be modular, and maybe even export some kind of module or library. `hevi` does this in an elegant way, exporting a zig module that makes it extremely easy to integrate with your zig application.

# Here comes hevi
`hevi` meets all the criteria we described.

Now, what *is* hevi?

> hevi is a modern, modular and minimalistic hex viewer.

That's exactly what it is. Just look at it, and its simple usage:
![image of example usage](https://raw.githubusercontent.com/Arnau478/hevi/7f9b8b040f4adc7f96d11add5cce3fde12cdd8eb/web/example.png)

One of the most remarkable features are the parsers. I've mentioned them briefly before, but here's an example. Just picture this. You're inspecting a Windows executable. Let's use `xxd` first. You write `xxd foo.exe | less`. You get this:

![xxd pe](https://private-user-images.githubusercontent.com/61841960/345958708-8c650697-d858-4c42-9f6e-6cbd157a1451.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MjAxMzE2NDMsIm5iZiI6MTcyMDEzMTM0MywicGF0aCI6Ii82MTg0MTk2MC8zNDU5NTg3MDgtOGM2NTA2OTctZDg1OC00YzQyLTlmNmUtNmNiZDE1N2ExNDUxLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDA3MDQlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwNzA0VDIyMTU0M1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTUzM2MyMjhjN2MwM2NkYTIyY2ViOGVlNTE2YTFiY2MxZGEwMzY3NmNmMjAzMTYzYzdkOWYzZjUxOTczMmFkMDYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.bT6NmYxJFhV2eZp1eUxFMlPOyLJICBh7bEuXYpuOGpQ)

What a mess! Oh, wait, let's add the `-R always` flag (which *obviously* stands for colo**r**ize).

![xxd pe force color](https://private-user-images.githubusercontent.com/61841960/345958998-849598f5-3a99-4aa2-9e96-a679d113ce74.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MjAxMzE3ODcsIm5iZiI6MTcyMDEzMTQ4NywicGF0aCI6Ii82MTg0MTk2MC8zNDU5NTg5OTgtODQ5NTk4ZjUtM2E5OS00YWEyLTllOTYtYTY3OWQxMTNjZTc0LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDA3MDQlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwNzA0VDIyMTgwN1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTViYWM2ZWI1YTRhNThhMDc5MGYxYTgwNDY2OGY5OTFjZDFhMDE5NWRiOWUyOGE5ZjA4NWI4ZGI5ODdmNTZkNzMmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.CWDl0-UsNvevJMO-0VU5vbQKOI3KYbTgyLKDQ0L0Ado)

Still, not great. Now let's use `hevi` instead of `xxd`:
![hevi pe parser](https://raw.githubusercontent.com/Arnau478/hevi/7f9b8b040f4adc7f96d11add5cce3fde12cdd8eb/web/parser.png)

You can easily see the headers, the sections it contains... You can even pretend like the executable doesn't contain a DOS stub for back-compatibility by just ignoring the brown blob!

Nice.

---

Well, that's pretty much everything I wanted to say. If you want to check it out, you can do so on [github](https://github.com/Arnau478/hevi).
