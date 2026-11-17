<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

![PS5 Password Generator](../assets/password/ps5-password.webp){ .app-logo }

# PS5 Password Generator

Makes a random password of **8 or 15 characters** with at least one capital letter, one small letter, one number and
one special character. The rules meet the minimum of NIST SP 800-63B and OWASP. NIST accepts 8 characters only for an
account that also has a second sign-in step, and asks for 15 characters where the password is the only step.

The password is **kept nowhere**: not in a file, not in a setting, not in a log. It is in the app's window until you
make a new one or close the app, and then it is gone for good. The app uses no network and needs no root.

## Install

Install it from the portal (the **Utilities** tab), or from a checkout of the repository:

```bash
bazzite-console/apps/password/install.sh                         # the app, its launcher, a menu entry and a Desktop icon
bazzite-console/apps/password/install.sh --no-desktop-shortcut   # without the Desktop icon
bazzite-console/apps/password/install.sh --uninstall             # remove it
```

The launcher is `~/.local/bin/ps5-password`; the app runs on the suite's shared Python environment.

## Using it

The app opens with a password of 8 characters, in large type under the top row. The top row, beside the icon:

| Pill | What it does |
|---|---|
| 8 characters | makes a new password of 8 characters, for an account that also has a second sign-in step. The one shown before is gone for good, and it leaves the clipboard too. |
| 15 characters | makes a new password of 15 characters, for an account where the password is the only step. The one shown before is gone for good, and it leaves the clipboard too. |
| Copy | puts the password on the clipboard for 60 seconds, so you can paste it where you keep your passwords |
| Clipboard | how many seconds the password stays on the clipboard, or **Empty** |

The state beside the app's name says where the password is: **Not stored** (only in the window), **Copied** (on the
clipboard too) or **Clipboard cleared**. You can also select the password in the window with the mouse.

**Store the password yourself**, in a password manager or on paper, before you make a new one or close the app.
Nothing can bring it back.

## The clipboard

**Copy** is a short stay, not a place to keep a password:

- After 60 seconds the app takes the password off the clipboard. It does the same when you make a new password and
  when you close the app.
- The app only clears its own password. What you copied somewhere else in the meantime stays on the clipboard.
- The password is marked as a secret, so the clipboard history of the Plasma desktop does not keep it. Another
  clipboard tool may not know the mark: check its history after you paste.

## The rules of a password

| Rule | Value |
|---|---|
| Length | 8 or 15 characters, as the pill you click says |
| Capital letters | at least one of `A` to `Z` |
| Small letters | at least one of `a` to `z` |
| Numbers | at least one of `0` to `9` |
| Special characters | at least one of <code>!"#$%&'()*+,-./:;<=>?@[&#92;]^_`{&#124;}~</code> |

- Every character is printable ASCII without the space, so you can type the password on any keyboard layout and
  every site takes the characters as they are. The special characters are the list of the
  [OWASP](https://owasp.org/www-community/password-special-characters) project.
- Capital and small letters, numbers and special characters together are the rule most sites and company policies
  ask for. The small letter is part of that rule, so the app adds it.
- The characters come from the system's cryptographic random source, and every password that meets the rules is as
  likely as any other. There are about 2.8 million billion passwords of 8 characters (51 bits), and about
  316 billion billion billion of 15 characters (98 bits).
- The app never shows the same password twice while it runs.

!!! note "8 or 15 characters"
    The rules meet the minimum of [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html) and the OWASP
    Application Security Verification Standard. NIST accepts 8 characters only for an account that also has a second
    sign-in step (a code from an app, a security key), and asks for 15 characters where the password is the only
    step. Choose **15 characters** when you are not sure, and turn on the second step where the site has one.
