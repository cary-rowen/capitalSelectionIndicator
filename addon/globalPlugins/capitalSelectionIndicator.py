# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2025 NV Access Limited, Cary-rowen

"""Capital Letter Indicators for Text Selection.

A prototype NVDA add-on that addresses GitHub issues #18360, #4874 and #12996.
Routes single-character selection through getSpellingSpeech to add capital
indicators (beep, pitch change, "cap" prefix).

Strategy: call getSpellingSpeech and strip CharacterModeCommand,
EndUtteranceCommand and SuppressUnicodeNormalizationCommand from the result
(since we cannot pass endsUtterance/useCharMode to the old API).
The localized prefix/suffix from the selection template is inserted as
independent str items so they remain outside any speech commands
(e.g. PitchCommand for capitals).
"""

import globalPluginHandler
import textInfos

import speech
from speech import speak, getSpellingSpeech
from speech.commands import (
	CharacterModeCommand,
	EndUtteranceCommand,
	SuppressUnicodeNormalizationCommand,
)
from speech.priorities import Spri
from speech.types import SpeechSequence

_originalSpeakSelectionChange = None

_STRIP_COMMANDS = (CharacterModeCommand, EndUtteranceCommand, SuppressUnicodeNormalizationCommand)


def _getCharSelectionSeq(char: str, locale: str) -> SpeechSequence:
	"""Get spelling speech for a single character, stripped of commands
	that should not appear in selection announcements.
	"""
	return [
		item
		for item in getSpellingSpeech(char, locale)
		if not isinstance(item, _STRIP_COMMANDS)
	]


def _speakCharSelection(
	template: str,
	char: str,
	locale: str,
	priority: Spri | None = None,
) -> None:
	"""Speak a single-character selection/unselection with capital indicators.

	:param template: The translated template string containing %s placeholder
		(e.g. "%s selected").
	:param char: The single character.
	:param locale: The locale for character processing.
	:param priority: The speech priority.
	"""
	seq = _getCharSelectionSeq(char, locale)
	prefix, sep, suffix = template.partition("%s")
	if not sep:
		seq = list(seq) + [template]
	else:
		# Insert prefix/suffix as separate items so they remain outside any
		# speech commands (e.g. PitchCommand for capitals).
		if prefix:
			seq.insert(0, prefix)
		if suffix:
			seq.append(suffix)
	speak(seq, symbolLevel=None, priority=priority)


def _patchedSpeakSelectionChange(
	oldInfo: textInfos.TextInfo,
	newInfo: textInfos.TextInfo,
	speakSelected: bool = True,
	speakUnselected: bool = True,
	generalize: bool = False,
	priority: Spri | None = None,
) -> None:
	"""Patched speakSelectionChange with capital indicators for single characters."""
	selectedTextList = []
	unselectedTextList = []
	if newInfo.isCollapsed and oldInfo.isCollapsed:
		return
	startToStart = newInfo.compareEndPoints(oldInfo, "startToStart")
	startToEnd = newInfo.compareEndPoints(oldInfo, "startToEnd")
	endToStart = newInfo.compareEndPoints(oldInfo, "endToStart")
	endToEnd = newInfo.compareEndPoints(oldInfo, "endToEnd")
	if speakSelected and oldInfo.isCollapsed:
		selectedTextList.append(newInfo.text)
	elif speakUnselected and newInfo.isCollapsed:
		unselectedTextList.append(oldInfo.text)
	else:
		if startToEnd > 0 or endToStart < 0:
			if speakSelected and not newInfo.isCollapsed:
				selectedTextList.append(newInfo.text)
			if speakUnselected and not oldInfo.isCollapsed:
				unselectedTextList.append(oldInfo.text)
		else:
			if speakSelected and startToStart < 0 and not newInfo.isCollapsed:
				tempInfo = newInfo.copy()
				tempInfo.setEndPoint(oldInfo, "endToStart")
				selectedTextList.append(tempInfo.text)
			if speakSelected and endToEnd > 0 and not newInfo.isCollapsed:
				tempInfo = newInfo.copy()
				tempInfo.setEndPoint(oldInfo, "startToEnd")
				selectedTextList.append(tempInfo.text)
			if startToStart > 0 and not oldInfo.isCollapsed:
				tempInfo = oldInfo.copy()
				tempInfo.setEndPoint(newInfo, "endToStart")
				unselectedTextList.append(tempInfo.text)
			if endToEnd < 0 and not oldInfo.isCollapsed:
				tempInfo = oldInfo.copy()
				tempInfo.setEndPoint(newInfo, "startToEnd")
				unselectedTextList.append(tempInfo.text)
	locale = speech.getCurrentLanguage()
	# Translators: This is spoken to indicate what has just been selected.
	selectedMsg = _("%s selected")
	if speakSelected:
		if not generalize:
			for text in selectedTextList:
				if len(text) == 1:
					_speakCharSelection(selectedMsg, text, locale, priority)
				else:
					speech.speakTextSelected(text, priority=priority)
		elif len(selectedTextList) > 0:
			text = newInfo.text
			if len(text) == 1:
				_speakCharSelection(selectedMsg, text, locale, priority)
			else:
				speech.speakTextSelected(text, priority=priority)
	if speakUnselected:
		if not generalize:
			for text in unselectedTextList:
				if len(text) == 1:
					# Translators: This is spoken to indicate what has been unselected.
					_speakCharSelection(_("%s unselected"), text, locale, priority)
				else:
					# Translators: This is spoken to indicate what has been unselected.
					speech.speakSelectionMessage(_("%s unselected"), text, priority=priority)
		elif len(unselectedTextList) > 0:
			if not newInfo.isCollapsed:
				text = newInfo.text
				if len(text) == 1:
					# Translators: This is spoken to indicate when the previous selection
					# was removed and a new selection was made.
					_speakCharSelection(_("%s selected instead"), text, locale, priority)
				else:
					# Translators: This is spoken to indicate when the previous selection
					# was removed and a new selection was made.
					speech.speakSelectionMessage(_("%s selected instead"), text, priority=priority)
			else:
				# Translators: Reported when selection is removed.
				speech.speakMessage(_("selection removed"), priority=priority)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Add-on entry point to add capital letter indicators for text selection."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		global _originalSpeakSelectionChange
		_originalSpeakSelectionChange = speech.speakSelectionChange
		speech.speakSelectionChange = _patchedSpeakSelectionChange

	def terminate(self):
		global _originalSpeakSelectionChange
		if _originalSpeakSelectionChange is not None:
			speech.speakSelectionChange = _originalSpeakSelectionChange
			_originalSpeakSelectionChange = None
		super().terminate()
