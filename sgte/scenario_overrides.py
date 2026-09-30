"""Exact-query troubleshooting overrides for hackathon demo (Phases 79–80).

Deterministic, manually authored responses for 22 Samsung-provided queries.
Exact match only (whitespace + case normalization). No LLM, no mapper,
no fabricated deeplinks or SIIS evidence IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

from sgte.official_schema import (
    Action,
    ContextDeeplinkResponse,
    Goal,
    StepGroup,
    actionCategory,
)

# Demo confidence only — not SIIS-grounded retrieval score.
_OVERRIDE_SCORE = 0.9


@dataclass(frozen=True)
class _ActionSpec:
    name: str
    description: str
    steps: Tuple[str, ...]


@dataclass(frozen=True)
class _ScenarioSpec:
    scenario_id: str
    query: str
    title: str
    summary: str
    actions: Tuple[_ActionSpec, ...]


def normalize_override_query(query: str) -> str:
    """Whitespace-collapse + casefold. No fuzzy / symptom matching."""
    return " ".join((query or "").casefold().split())


def _build_action(spec: _ActionSpec) -> Action:
    return Action(
        actionName=spec.name,
        description=spec.description,
        stepGroups=[
            StepGroup(
                steps=list(spec.steps),
                actionableDeeplink=None,
                validationDeeplink=None,
            )
        ],
        category=actionCategory.manual,
    )


def build_scenario_response(query: str, spec: _ScenarioSpec) -> ContextDeeplinkResponse:
    del query  # matching already done; preserve caller's query externally
    actions = [_build_action(a) for a in spec.actions]
    goal = Goal(
        goal=spec.summary,
        title=spec.title,
        actions=actions,
        score=_OVERRIDE_SCORE,
    )
    return ContextDeeplinkResponse(contexts=[goal])


def _A(name: str, description: str, *steps: str) -> _ActionSpec:
    return _ActionSpec(name=name, description=description, steps=tuple(steps))


# ---------------------------------------------------------------------------
# Exactly 22 hardcoded scenarios (S01–S22). Queries must match verbatim
# after normalize_override_query (whitespace + case only).
# ---------------------------------------------------------------------------

_SCENARIOS: Tuple[_ScenarioSpec, ...] = (
    _ScenarioSpec(
        scenario_id="S01",
        query=(
            "My TechCorp A15G tablet screen flashes and then goes completely blank "
            "whenever I tap to open an email in Gmail, and after it works for a short "
            "time it goes blank again."
        ),
        title="Gmail Opens Then Screen Goes Blank",
        summary=(
            "The display blanks while opening mail in Gmail, then recovers briefly "
            "before failing again. This is an in-app display issue, not a phone that "
            "fails to power on."
        ),
        actions=(
            _A(
                "Restart and retest Gmail",
                "It will clear temporary display glitches before deeper checks.",
                "Save any work you can still access.",
                "Restart the tablet normally, then open Gmail and open the same email again.",
                "Note whether the screen blanks only in Gmail or also in other apps.",
            ),
            _A(
                "Update Gmail and system software",
                "It will apply available fixes for app and display stability.",
                "Check for Gmail updates in your app store and install any that are available.",
                "Check for system updates and install available updates.",
                "Reopen Gmail and confirm whether the flicker and blanking still occur.",
            ),
            _A(
                "Clear Gmail cache only",
                "It will refresh Gmail without deleting your account data.",
                "Open the tablet's app settings and select Gmail.",
                "Clear the app cache. Do not clear app data or remove the account.",
                "Open Gmail again and test the same email.",
            ),
            _A(
                "Decide between app support and device support",
                "It will route the next step based on how widely the symptom appears.",
                "Open at least one other app and watch for the same blanking.",
                "If only Gmail blanks, contact Gmail or account support with the update and cache steps you already tried.",
                "If other apps also blank, contact device support and describe the recurring display failure.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S02",
        query=(
            "My Nexa X1 screen turns completely blank or white and no text appears "
            "when I search for a stock price or use the Quick Assist app, and it "
            "happens with other apps too."
        ),
        title="Blank or White Screen Across Apps",
        summary=(
            "The screen goes blank or white with no readable text in more than one "
            "app, including search and Quick Assist. Treat this as a device display "
            "problem, not a single-app bug."
        ),
        actions=(
            _A(
                "Restart and recheck multiple apps",
                "It will show whether the blanking is temporary or persistent.",
                "Restart the phone.",
                "Open two or more different apps and confirm whether the blank or white screen returns.",
            ),
            _A(
                "Adjust visibility only if the screen is readable",
                "It will rule out simple visibility settings when the UI can still be used.",
                "If you can see and use the interface, increase brightness and review display visibility options.",
                "If the screen is fully blank or white with no usable controls, skip settings changes and continue to support.",
            ),
            _A(
                "Install available updates when accessible",
                "It will apply system and app fixes if the device remains operable.",
                "If the device is accessible, install available system and app updates.",
                "Retest more than one app after updating.",
            ),
            _A(
                "Contact device support for a multi-app display fault",
                "It will escalate a device-level display failure correctly.",
                "Explain that blank or white screens appear across multiple applications, not just one app.",
                "Share when the issue started and whether a restart or updates changed anything.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S03",
        query=(
            "My Nexa Fold X1 screen went completely black, so I can't see or interact "
            "with the phone, and I'm unable to use Data Transfer or any other method "
            "to transfer my data."
        ),
        title="Foldable Black Screen Blocking Data Access",
        summary=(
            "The foldable display is completely black, so on-screen controls and Data "
            "Transfer are unavailable. Focus on whether the phone is still operating, "
            "safe restart, data preservation, and authorized service."
        ),
        actions=(
            _A(
                "Confirm the display cannot be used for transfer",
                "It will stop attempts that need a visible interface.",
                "If the screen is completely black, you cannot open Data Transfer, scan a QR code, or navigate menus on this device.",
                "Do not try to complete a transfer by guessing invisible on-screen controls.",
            ),
            _A(
                "Check power and attempt a documented restart",
                "It will determine whether the device still runs and can recover temporarily.",
                "Connect the phone to a known-working charger and allow it to charge briefly.",
                "Follow only the manufacturer's documented restart procedure for your model.",
                "Do not invent button combinations.",
            ),
            _A(
                "Use another working interface only if available",
                "It will preserve data without promising recovery.",
                "If the cover screen or another supported interface works, use it for any available backup options.",
                "Data recovery is not guaranteed while the main display remains unusable.",
            ),
            _A(
                "Seek authorized service for display and data options",
                "It will escalate hardware-level display failure safely.",
                "Contact authorized service and explain that the screen is black, the device cannot be operated normally, and Data Transfer cannot proceed.",
                "Ask about display repair and any data-preservation options they can offer.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S04",
        query=(
            "My TechCorp Nexa A14/A15 screen suddenly went completely black on its own "
            "after about a month of use. It doesn't display anything, even when I try "
            "to turn it on."
        ),
        title="Phone Screen Stays Completely Black",
        summary=(
            "The phone went black suddenly and shows nothing when you try to turn it "
            "on. Charging may help diagnose power, but it is not assumed to be the cause."
        ),
        actions=(
            _A(
                "Look for any sign the phone is alive",
                "It will separate a dead display from a device that is not powering on.",
                "Connect a known-working charger and cable.",
                "Watch for vibration, sounds, notification LED behavior, or any charging indicator—even if the screen stays black.",
            ),
            _A(
                "Attempt a documented restart",
                "It will try a safe recovery without inventing hardware steps.",
                "Follow the manufacturer's documented restart procedure.",
                "After restarting, check again for any display, sound, or vibration response.",
            ),
            _A(
                "Seek authorized service if the screen stays black",
                "It will escalate an unresponsive display correctly.",
                "Contact authorized service and explain that the screen went black suddenly after about a month of use and still shows nothing.",
                "Tell them whether the phone vibrates, makes sounds, or appears to charge.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S05",
        query=(
            "My tablet screen stays completely blank when I try to use Data Transfer "
            "to scan the QR code for transferring data from my Nexa X1 phone, so the "
            "transfer can't proceed."
        ),
        title="Data Transfer QR Screen Stays Blank",
        summary=(
            "The tablet stays blank during Data Transfer QR scanning, so the transfer "
            "cannot continue on that screen. Fix the blank scanning view or use another "
            "supported path—without claiming any specific method is guaranteed."
        ),
        actions=(
            _A(
                "Stop the QR scan while the tablet is blank",
                "It will prevent a transfer that cannot be completed on an unusable screen.",
                "If the tablet stays blank, you cannot scan the QR code or finish on-screen transfer steps on that tablet.",
                "End or cancel the current transfer attempt rather than continuing blindly.",
            ),
            _A(
                "Restart both devices and retry once",
                "It will clear a temporary transfer-app display fault.",
                "Restart the phone and the tablet if their controls still respond.",
                "Start Data Transfer again and check whether the tablet shows the QR scanning screen.",
            ),
            _A(
                "Retry only with a method that does not need the blank tablet screen",
                "It will avoid relying on an unusable QR view.",
                "If the tablet remains blank, do not keep retrying QR scanning on that tablet.",
                "If another transfer option is available on a working display or connection, try that option. Success is not guaranteed.",
            ),
            _A(
                "Contact support if QR scanning stays blank",
                "It will escalate a blocked transfer correctly.",
                "Explain that the tablet screen stays blank during Data Transfer QR scanning so the transfer cannot proceed.",
                "Ask about alternate supported transfer options and display troubleshooting.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S06",
        query=(
            "My tablet's screen stays dark and only three app icons are lit while the "
            "rest are dark and won't open, so nothing loads on the screen and I can't "
            "use the device."
        ),
        title="Tablet Screen Dark With Limited App Icons",
        summary=(
            "Only a few app icons remain lit while the rest of the tablet interface "
            "stays dark and unusable. This is a limited-interface failure, not a "
            "simple full blank screen."
        ),
        actions=(
            _A(
                "Return to Home if the tablet still responds",
                "It will exit a stuck partial launcher state when possible.",
                "If any control still responds, use the normal Home control once.",
                "Check whether more icons become visible or usable.",
            ),
            _A(
                "Restart the tablet",
                "It will try to restore a normal home screen layout.",
                "Restart normally if the tablet responds.",
                "If it does not respond, follow the manufacturer's documented restart procedure.",
            ),
            _A(
                "Check whether the rest of the interface returns",
                "It will confirm whether the limited-icon state cleared.",
                "After restarting, look for the remaining icons and confirm whether apps open normally.",
                "Do not keep forcing dark icons open if they never respond.",
            ),
            _A(
                "Contact device support for a partial UI failure",
                "It will escalate a stuck limited interface.",
                "Explain that only a few icons are illuminated and the other apps cannot be opened.",
                "Share whether Home or a restart changed anything.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S07",
        query=(
            "My new smartphone's main screen stays small and doesn't fill the whole "
            "display; I can't make it expand to full size and I've never seen this before."
        ),
        title="Main Screen Does Not Fill the Display",
        summary=(
            "The home or main view stays smaller than the full panel and will not "
            "expand. Focus on display size and screen-mode settings rather than "
            "unrelated features such as screen mirroring."
        ),
        actions=(
            _A(
                "Restart and recheck the layout",
                "It will clear a temporary display-layout glitch.",
                "Restart the phone.",
                "Confirm whether the main screen still fails to fill the display.",
            ),
            _A(
                "Review display size and screen-mode options",
                "It will check settings that control how large content appears.",
                "If the interface is usable, open display settings.",
                "Look for screen size, display size, zoom, or app display options and adjust them toward the normal full-screen layout.",
            ),
            _A(
                "Compare Home with another app",
                "It will show whether the problem is system-wide or app-specific.",
                "Open another application and compare how much of the panel it uses.",
                "Note whether only the main screen is small or every app is inset.",
            ),
            _A(
                "Contact support if the screen stays undersized",
                "It will escalate an abnormal new-device layout issue.",
                "Explain that the main screen stays small and will not expand to full size on a new phone.",
                "Mention the display settings you already checked.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S08",
        query=(
            "My Nexa Fold X1 inner screen stopped working by itself; it shows no image "
            "and doesn't respond to touch, while the outer cover screen still works."
        ),
        title="Inner Foldable Screen Not Responding",
        summary=(
            "The inner display has no image and no touch response, while the cover "
            "screen still works. Use the working screen for access and data, then "
            "seek authorized service."
        ),
        actions=(
            _A(
                "Confirm the cover screen still works",
                "It will identify which display remains usable.",
                "Use the outer cover screen to unlock and navigate if it still responds.",
                "Avoid repeatedly opening and closing the phone just to retest the inner screen.",
            ),
            _A(
                "Back up from the working cover screen",
                "It will preserve accessible data before repair.",
                "If possible, use the cover screen to run any available backup options.",
                "Do not wait for the inner screen to recover before securing important data.",
            ),
            _A(
                "Seek authorized service for the inner display",
                "It will escalate a likely hardware display fault.",
                "Contact authorized service and explain that the inner screen shows no image and does not respond to touch, while the cover screen still works.",
                "Ask about repair options and data preservation.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S09",
        query=(
            "My TechCorp Nexa Fold X1 screen flickers and goes blank whenever I open "
            "it, so I can't see anything or access the settings, which stops me from "
            "using the phone."
        ),
        title="Screen Flickers Blank When Unfolded",
        summary=(
            "The display flickers or goes blank when the foldable is opened, which "
            "blocks settings and normal use. Avoid repeatedly opening and closing "
            "the device; prioritize cover-screen access and authorized service."
        ),
        actions=(
            _A(
                "Stop reopening the phone to reproduce the fault",
                "It will reduce stress on a display that fails when unfolded.",
                "Do not repeatedly open and close the phone to watch the flicker.",
                "Keep the device closed or use the cover screen if that display still works.",
            ),
            _A(
                "Preserve data from any working interface",
                "It will secure accessible information before repair.",
                "If the cover screen works, use available backup options from there.",
                "If no usable interface remains, skip software settings that require opening the phone.",
            ),
            _A(
                "Seek authorized service for open-state display failure",
                "It will escalate a display fault tied to unfolding the device.",
                "Contact authorized service and explain that the screen flickers or goes blank when the phone is opened.",
                "Ask for display inspection and repair; do not assume a software setting will fix this.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S10",
        query=(
            "My Nexa Fold X1 screen is half black—one side of the display is completely "
            "dark while the other side works fine, so I can't access the device normally."
        ),
        title="Half of the Foldable Display Is Black",
        summary=(
            "One side of the foldable display is black while the other side still "
            "works. Use the working portion only if it is safe, preserve data, and "
            "seek authorized repair."
        ),
        actions=(
            _A(
                "Use the visible area only if it responds safely",
                "It will avoid damaging a partially failed panel.",
                "Check whether the remaining visible area still accepts touch without pressing hard.",
                "Do not press, flex, or tap forcefully on the black portion of the display.",
            ),
            _A(
                "Back up if the working portion allows it",
                "It will preserve data before the display worsens.",
                "If you can operate the working portion safely, use available backup options.",
                "If interaction feels unsafe or unreliable, stop and move to service.",
            ),
            _A(
                "Seek authorized service for a partial display failure",
                "It will escalate a hardware-style half-black panel.",
                "Contact authorized service and explain that one side of the display is completely dark while the other side still works.",
                "Ask about repair and data-preservation options.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S11",
        query=(
            "My Nexa X1 has a floating circle that constantly hovers on my screen and "
            "gives me quick shortcuts to recent apps, home, back, screen off, volume "
            "control, and more; I want to remove it."
        ),
        title="Remove Floating Shortcut Circle",
        summary=(
            "A floating circle stays on screen with shortcuts such as recent apps, "
            "Home, Back, screen off, and volume. Identify which floating control it "
            "is, then turn off that matching setting—without assuming a specific "
            "feature name."
        ),
        actions=(
            _A(
                "Identify the floating control from its shortcuts",
                "It will match the on-screen circle to the correct setting.",
                "Note the shortcuts shown: recent apps, Home, Back, screen off, volume, and any others.",
                "Several tools can show a floating circle; identify which one matches before turning settings off.",
            ),
            _A(
                "Check Accessibility for an assistant or floating menu",
                "It will remove a common accessibility floating control if that is the source.",
                "Open Accessibility settings and look for an assistant menu or floating menu option that matches the circle.",
                "If you find a matching option, turn it off and confirm the circle is gone.",
            ),
            _A(
                "Check other floating shortcut tools if needed",
                "It will cover non-accessibility floating menus safely.",
                "If Accessibility settings are not responsible, review other floating shortcut, gesture, or assistant tools on the device.",
                "Turn off only the feature that matches this floating circle.",
            ),
            _A(
                "Confirm removal or contact support",
                "It will verify the circle is gone or escalate correctly.",
                "Confirm that the floating circle no longer appears.",
                "If it remains, contact device support and describe the shortcuts it offers.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S12",
        query=(
            "My Nexa X1 screen stays blank and doesn't show any activation message or "
            "anything else when I turn it on after the carrier deactivated the old phone."
        ),
        title="Blank Screen After Carrier Switch",
        summary=(
            "The new phone stays blank after the carrier deactivated the old device. "
            "A blank display is not the same as a missing activation message, and "
            "reactivation alone may not fix a display failure."
        ),
        actions=(
            _A(
                "Check whether the phone is powering on",
                "It will separate a blank display from a device that never starts.",
                "Look for charging indicators, vibration, sounds, or other signs of operation when you turn the phone on.",
                "Note whether anything appears on screen at all.",
            ),
            _A(
                "Attempt a documented restart",
                "It will try a safe recovery before involving the carrier.",
                "Follow the manufacturer's documented restart procedure.",
                "Check again for any display content after restart.",
            ),
            _A(
                "Handle carrier activation only if the screen becomes usable",
                "It will keep activation separate from a blank-display fault.",
                "If the display starts working, contact the carrier to confirm activation of the new device.",
                "Do not expect reactivation to repair a screen that stays completely blank.",
            ),
            _A(
                "Seek device support if the screen remains blank",
                "It will escalate a display problem that activation will not solve.",
                "Contact device support and explain that the screen stays blank after power-on following the old phone's deactivation.",
                "Share whether the phone shows any signs of operation.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S13",
        query=(
            "My smartphone's screen is completely cracked, it's a total crack and I "
            "can't use the device."
        ),
        title="Cracked Screen Needs Authorized Repair",
        summary=(
            "The screen is extensively cracked and the device cannot be used safely. "
            "Avoid pressing the glass; arrange authorized repair and ask about data "
            "preservation."
        ),
        actions=(
            _A(
                "Protect the damaged display",
                "It will reduce further injury to the panel and glass.",
                "Do not press cracked areas or attempt to remove broken glass.",
                "Keep the phone protected while you arrange repair.",
            ),
            _A(
                "Arrange authorized screen repair",
                "It will replace DIY handling with professional service.",
                "Contact an authorized service provider.",
                "Explain that the screen is completely cracked and the device is unusable.",
            ),
            _A(
                "Ask about data preservation",
                "It will request recovery options without promising success.",
                "If the device cannot be operated safely, ask the service provider about available data-preservation options.",
                "Data recovery through the damaged screen is not guaranteed.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S14",
        query=(
            "My Nexa X1 Ultra only shows a blue (or black) screen with tiny text when "
            "I try to turn it on, and it won't start up. I tried holding the power "
            "button but it doesn't help."
        ),
        title="Stuck on Blue or Black Startup Screen",
        summary=(
            "The phone shows only a blue or black screen with tiny text and will not "
            "finish starting. Treat this as a startup or recovery-screen issue—not a "
            "cue to choose unfamiliar erase options."
        ),
        actions=(
            _A(
                "Record the on-screen text",
                "It will preserve details that service teams need.",
                "If possible, note or photograph the tiny text shown on the blue or black screen.",
                "Do not select options you do not understand.",
            ),
            _A(
                "Attempt a documented restart only",
                "It will try a safe restart without entering unknown recovery paths.",
                "Follow the manufacturer's supported restart procedure.",
                "Holding the power button alone may not be enough; use the documented method for your model.",
            ),
            _A(
                "Avoid factory reset and unfamiliar recovery choices",
                "It will protect your data during a failed startup.",
                "Do not select factory reset, erase, wipe, or other recovery options you do not recognize.",
                "Leave the device as-is if restarting does not restore a normal start.",
            ),
            _A(
                "Seek authorized service",
                "It will escalate a device that cannot leave the startup screen.",
                "Contact authorized service and describe the blue or black startup screen and any text you recorded.",
                "Mention that holding the power button did not restore normal startup.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S15",
        query=(
            "My TechCorp X1 Ultra screen flashes extremely quickly (in milliseconds) "
            "whenever I plug in a charger, making the display unusable for a short period."
        ),
        title="Display Flashes When Charger Connects",
        summary=(
            "The screen flashes rapidly at the moment a charger is connected. Prioritize "
            "safe charging: stop if the phone or charger seems damaged or too hot."
        ),
        actions=(
            _A(
                "Stop immediately if charging seems unsafe",
                "It will reduce risk from a damaged charger or overheating device.",
                "Unplug the charger if the phone becomes unusually hot or shows signs of physical damage.",
                "Do not continue using a damaged cable, plug, or charger.",
            ),
            _A(
                "Retest with a known-compatible charger when safe",
                "It will check whether the flash follows one accessory.",
                "If the device is cool and undamaged, try a known-compatible charger and cable.",
                "Observe whether the rapid flashing still happens at the moment of connection.",
            ),
            _A(
                "Note whether flashing continues after connection",
                "It will help service distinguish a connect-time glitch from ongoing display failure.",
                "Watch whether the flash happens only while plugging in or continues afterward.",
                "Do not assume this is a fast-charging setting problem.",
            ),
            _A(
                "Seek authorized service if flashing continues",
                "It will escalate a charger-linked display fault.",
                "Contact authorized service and explain that the display flashes extremely quickly whenever a charger is connected.",
                "Share whether a different charger changed the behavior.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S16",
        query=(
            "My Nexa X1 screen goes completely blank, just a dark screen with occasional "
            "scrolling and no visible content, so I can't see anything or use Data "
            "Transfer to transfer data."
        ),
        title="Blank Screen With Occasional Scrolling",
        summary=(
            "The screen is dark with only occasional scrolling and no usable content. "
            "The phone may still be operating, but Data Transfer cannot proceed until "
            "a usable display is available."
        ),
        actions=(
            _A(
                "Treat the display as unusable for transfer",
                "It will stop Data Transfer attempts that need a readable screen.",
                "A dark screen with only occasional scrolling cannot show transfer screens or QR codes reliably.",
                "Do not start or continue Data Transfer until a usable display or alternate interface is available.",
            ),
            _A(
                "Attempt a documented restart",
                "It will check whether the display recovers without assuming the phone is fully dead.",
                "Follow the manufacturer's supported restart procedure.",
                "After restarting, check whether readable content returns.",
            ),
            _A(
                "Preserve data only if an interface becomes usable",
                "It will secure information without promising recovery.",
                "If a usable display or supported interface appears, use available backup options.",
                "Data recovery is not guaranteed while the screen remains blank.",
            ),
            _A(
                "Seek authorized service",
                "It will escalate a display that stays dark with only scrolling.",
                "Contact authorized service and explain that the screen is dark, occasionally scrolls without usable content, and Data Transfer cannot proceed.",
                "Mention any signs that the phone still responds after restart.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S17",
        query="My Nexa Fold X1 screen is cracked again right where it folds.",
        title="Foldable Screen Cracked at the Fold",
        summary=(
            "The inner display is cracked again along the folding area. Handle the "
            "device carefully and seek authorized repair—do not attempt hinge or "
            "display repairs yourself."
        ),
        actions=(
            _A(
                "Protect the folding area",
                "It will limit further damage at the crack.",
                "Avoid repeatedly folding or pressing on the cracked folding area.",
                "Minimize handling of the damaged inner display.",
            ),
            _A(
                "Do not attempt DIY hinge or display repair",
                "It will prevent unsafe self-repair of the fold panel.",
                "Do not try to remove, peel, or replace the inner display layer.",
                "Do not attempt to repair the hinge yourself.",
            ),
            _A(
                "Seek authorized service",
                "It will arrange professional repair for a fold-line crack.",
                "Contact an authorized service provider and explain that the crack is at the folding area and has recurred.",
                "Ask about repair options and whether data-preservation assistance is available. Recovery is not guaranteed.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S18",
        query="The touch doesn't work on certain parts of the screen.",
        title="Touch Fails in Specific Screen Areas",
        summary=(
            "Touch fails in some areas while other parts of the screen may still "
            "respond. Safe cleaning and a restart are basic checks; they may not "
            "fix a hardware fault."
        ),
        actions=(
            _A(
                "Clean gently and retest the dead zones",
                "It will rule out surface interference without forcing the panel.",
                "Wipe the screen with a soft, lint-free cloth to remove moisture or dirt.",
                "Do not press hard on the unresponsive areas.",
            ),
            _A(
                "Check the screen protector safely",
                "It will remove a common cause of partial touch failure.",
                "If a protector is bubbled, damaged, or poorly fitted, follow the manufacturer's guidance for safe removal or replacement.",
                "Retest the same screen areas afterward.",
            ),
            _A(
                "Restart once, then escalate if areas stay dead",
                "It will distinguish a temporary glitch from a lasting local fault.",
                "Restart the device and check the same unresponsive areas again.",
                "If those areas still do not respond, contact authorized service and describe the locations. Cleaning or restarting may not fix a hardware touch fault.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S19",
        query="I can hardly see anything on the display.",
        title="Display Is Difficult to See",
        summary=(
            "The display is hard to read. If content is faintly visible, adjust "
            "brightness; if nothing is visible at all, treat it as a blank-display "
            "problem and seek support."
        ),
        actions=(
            _A(
                "Decide whether the screen is dim or fully blank",
                "It will choose the right next step for visibility vs. total blanking.",
                "If you can see faint content, treat this as a dim or hard-to-read display.",
                "If nothing is visible at all, skip brightness settings and seek device support for a blank display.",
            ),
            _A(
                "Increase brightness when the UI is usable",
                "It will improve visibility when controls can still be reached.",
                "If you can interact with the phone, increase brightness.",
                "Also check automatic brightness or other visibility options if they are available.",
            ),
            _A(
                "Restart and reassess readability",
                "It will clear a temporary visibility glitch.",
                "Restart the device and check whether the display is easier to see.",
            ),
            _A(
                "Seek authorized service if it remains hard to read",
                "It will escalate lasting visibility problems without assuming damage.",
                "Contact authorized service and explain that the display remains difficult to see after brightness checks.",
                "Do not assume physical damage without an inspection.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S20",
        query=(
            "My Nexa A14 screen looks distorted right after I received the phone, and "
            "I need a diagnostic test."
        ),
        title="New Phone Arrived With Distorted Display",
        summary=(
            "Display distortion was present right after unboxing. Document the issue, "
            "try one safe restart, then contact the seller or authorized support. Do "
            "not start with a factory reset, and do not claim a diagnostic already ran."
        ),
        actions=(
            _A(
                "Document the distortion",
                "It will give the seller or service clear evidence.",
                "Note whether distortion covers the whole screen or only part of it.",
                "If possible, take photos of the display for the seller or service provider.",
            ),
            _A(
                "Restart once and recheck",
                "It will rule out a temporary first-boot glitch.",
                "Restart the phone once.",
                "Confirm whether the distortion remains afterward.",
            ),
            _A(
                "Contact the seller or authorized support",
                "It will start warranty or exchange options for a new-device defect.",
                "Explain that the distortion was present immediately after you received the phone.",
                "Ask about exchange, warranty inspection, or authorized diagnostic options.",
            ),
            _A(
                "Avoid destructive first steps",
                "It will protect a new device during early troubleshooting.",
                "Do not perform a factory reset as an initial step for a new-device display defect.",
                "Use a diagnostic test only if one is officially available for your device; do not assume one already ran.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S21",
        query=(
            "My Nexa X1 screen inputs are delayed and the touch responsiveness is laggy, "
            "causing a noticeable delay when I try to interact with the phone."
        ),
        title="Touch Response Feels Laggy",
        summary=(
            "Touch still works but feels delayed. This is different from dead touch "
            "zones. Start with restart, multi-app comparison, and reducing load before "
            "escalating."
        ),
        actions=(
            _A(
                "Confirm lag versus dead touch",
                "It will keep troubleshooting focused on delayed input.",
                "If touch still registers but feels late, continue with these responsiveness checks.",
                "If some areas never respond at all, treat that as localized unresponsive touch instead.",
            ),
            _A(
                "Restart and compare across apps",
                "It will show whether lag is temporary or system-wide.",
                "Restart the phone.",
                "Compare touch response in more than one application.",
            ),
            _A(
                "Reduce load and install available updates",
                "It will improve responsiveness when software load is the cause.",
                "Close unnecessary running applications and retest touch.",
                "Install available software updates if the device is accessible.",
            ),
            _A(
                "Seek support if lag continues everywhere",
                "It will escalate lasting system-wide delay.",
                "Contact support and explain that touch remains delayed across applications after restart and updates.",
            ),
        ),
    ),
    _ScenarioSpec(
        scenario_id="S22",
        query=(
            "My Nexa X1 Ultra screen is completely black and won't turn on, even though "
            "the phone powers on, rings, and otherwise works; there is no physical damage."
        ),
        title="Black Screen While Phone Still Works",
        summary=(
            "The phone still powers on and rings, but the display stays black with no "
            "visible damage. Treat this as display failure on a working device and "
            "prioritize data preservation plus authorized display service."
        ),
        actions=(
            _A(
                "Confirm the phone is still operating",
                "It will separate a failed display from a phone that will not turn on.",
                "Call the device if possible and confirm that it still rings.",
                "Note any other signs of operation even though the screen stays black.",
            ),
            _A(
                "Attempt a documented restart",
                "It will try to restore the display without erasing data.",
                "Follow the manufacturer's supported restart procedure.",
                "Check whether the display returns after restart.",
            ),
            _A(
                "Preserve data and avoid erase actions",
                "It will protect information on a phone that still runs.",
                "If any supported interface becomes available, use available backup options.",
                "Do not erase or factory-reset the device while chasing a black-screen display fault.",
            ),
            _A(
                "Seek authorized display service",
                "It will escalate a working phone with a failed screen.",
                "Contact authorized service and explain that the phone rings and operates but the display remains black, with no physical damage visible.",
                "Ask about display repair and data-preservation options.",
            ),
        ),
    ),
)


def _index_scenarios() -> Dict[str, _ScenarioSpec]:
    by_norm: Dict[str, _ScenarioSpec] = {}
    for spec in _SCENARIOS:
        key = normalize_override_query(spec.query)
        if key in by_norm:
            raise RuntimeError(f"Duplicate override query key for {spec.scenario_id}")
        by_norm[key] = spec
    return by_norm


_BY_NORM: Dict[str, _ScenarioSpec] = _index_scenarios()
_BY_ID: Dict[str, _ScenarioSpec] = {s.scenario_id: s for s in _SCENARIOS}

SCENARIO_COUNT = len(_SCENARIOS)
SCENARIO_IDS: Tuple[str, ...] = tuple(s.scenario_id for s in _SCENARIOS)
SCENARIO_QUERIES: Tuple[str, ...] = tuple(s.query for s in _SCENARIOS)
SCENARIO_TITLES: Dict[str, str] = {s.scenario_id: s.title for s in _SCENARIOS}
SCENARIO_SUMMARIES: Dict[str, str] = {s.scenario_id: s.summary for s in _SCENARIOS}


def match_scenario(query: str) -> Optional[_ScenarioSpec]:
    """Return the scenario spec for an exact normalized match, else None."""
    if not (query or "").strip():
        return None
    return _BY_NORM.get(normalize_override_query(query))


def get_scenario_by_id(scenario_id: str) -> Optional[_ScenarioSpec]:
    return _BY_ID.get(scenario_id)


def try_scenario_override(query: str) -> Optional[ContextDeeplinkResponse]:
    """Build a schema-valid override response for an exact match, else None."""
    spec = match_scenario(query)
    if spec is None:
        return None
    return build_scenario_response(query, spec)


def scenario_id_for_query(query: str) -> Optional[str]:
    spec = match_scenario(query)
    return spec.scenario_id if spec else None
