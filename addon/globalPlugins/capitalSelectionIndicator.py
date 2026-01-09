# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2025 NV Access Limited, Cary-rowen

"""Capital Letter Indicators for Text Selection.

A prototype NVDA add-on that addresses GitHub issues #4874 and #12996.
This add-on adds capital letter indicators (beep, pitch change, "cap" prefix)
when selecting single characters, matching the behavior of character navigation.
"""

from typing import Optional

import globalPluginHandler
import textInfos

import characterProcessing
import config
import speech
from speech import speak, _getSpellingCharAddCapNotification
from speech.commands import PitchCommand
from speech.priorities import Spri
from speech.types import SpeechSequence
from synthDriverHandler import getSynth


_originalSpeakSelectionChange = None


def _buildSpeechFromTemplate(
	template: str,
	charSequence: SpeechSequence,
) -> SpeechSequence:
	"""Build a speech sequence by parsing a template string with %s placeholder.

	This allows reusing NVDA's existing translated strings like "%s selected" or "selected %s"
	while inserting the character sequence (with capital indicators) at the correct position.

	:param template: The translated template string containing %s placeholder.
	:param charSequence: The speech sequence for the character (with capital indicators).
	:return: Complete speech sequence with the character inserted at the placeholder position.
	"""
	if "%s" not in template:
		return list(charSequence) + [template]

	before, after = template.split("%s", 1)
	result: SpeechSequence = []

	if before:
		result.append(before)
	result.extend(charSequence)
	if after:
		result.append(after)

	return result


def _getSingleCharSelectionSpeech(
	char: str,
	locale: str,
	messageTemplate: Optional[str] = None,
) -> SpeechSequence:
	"""Get speech sequence for a single selected/unselected character with capital indicators.

	Uses NVDA's existing L{_getSpellingCharAddCapNotification} for seamless integration,
	and supports template strings for translation flexibility.

	:param char: The single character that was selected/unselected.
	:param locale: The locale for character processing.
	:param messageTemplate: The translated template with %s placeholder (e.g., "%s selected").
		If None, defaults to NVDA's existing _("%s selected") string.
	:return: Speech sequence with capital indicators and the message.
	"""
	if messageTemplate is None:
		# Translators: This is spoken to indicate what has just been selected.
		# The text preceding 'selected' is intentional.
		# For example 'hello world selected'
		messageTemplate = _("%s selected")

	synth = getSynth()
	if synth is None:
		speakCharAs = characterProcessing.processSpeechSymbol(locale, char)
		return _buildSpeechFromTemplate(messageTemplate, [speakCharAs])

	synthConfig = config.conf["speech"][synth.name]

	if PitchCommand in synth.supportedCommands:
		capPitchChange = synthConfig["capPitchChange"]
	else:
		capPitchChange = 0
	sayCapForCapitals = synthConfig["sayCapForCapitals"]
	beepForCapitals = synthConfig["beepForCapitals"]

	speakCharAs = characterProcessing.processSpeechSymbol(locale, char)
	uppercase = char.isupper()

	charSequence: SpeechSequence = list(
		_getSpellingCharAddCapNotification(
			speakCharAs,
			uppercase and sayCapForCapitals,
			capPitchChange if uppercase else 0,
			uppercase and beepForCapitals,
		)
	)

	return _buildSpeechFromTemplate(messageTemplate, charSequence)


def _speakSingleCharSelected(
	char: str,
	locale: str,
	priority: Optional[Spri] = None,
) -> None:
	"""Speak a single selected character with capital indicators.

	:param char: The single character that was selected.
	:param locale: The locale for character processing.
	:param priority: The speech priority.
	"""
	seq = _getSingleCharSelectionSpeech(char, locale)
	if seq:
		speak(seq, symbolLevel=None, priority=priority)


def _speakSingleCharUnselected(
	char: str,
	locale: str,
	priority: Optional[Spri] = None,
) -> None:
	"""Speak a single unselected character with capital indicators.

	:param char: The single character that was unselected.
	:param locale: The locale for character processing.
	:param priority: The speech priority.
	"""
	# Translators: This is spoken to indicate what has been unselected. for example 'hello unselected'
	seq = _getSingleCharSelectionSpeech(char, locale, messageTemplate=_("%s unselected"))
	if seq:
		speak(seq, symbolLevel=None, priority=priority)


def _patchedSpeakSelectionChange(
	oldInfo: textInfos.TextInfo,
	newInfo: textInfos.TextInfo,
	speakSelected: bool = True,
	speakUnselected: bool = True,
	generalize: bool = False,
	priority: Optional[Spri] = None,
) -> None:
	"""Patched version of speakSelectionChange with capital letter indicators for single characters.

	:param oldInfo: A TextInfo instance representing what the selection was before.
	:param newInfo: A TextInfo instance representing what the selection is now.
	:param speakSelected: Whether to speak selected text.
	:param speakUnselected: Whether to speak unselected text.
	:param generalize: If True, changes need to be spoken more generally.
	:param priority: The speech priority.
	"""
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

	if speakSelected:
		if not generalize:
			for text in selectedTextList:
				if len(text) == 1:
					_speakSingleCharSelected(text, locale, priority=priority)
				else:
					speech.speakTextSelected(text, priority=priority)
		elif len(selectedTextList) > 0:
			text = newInfo.text
			if len(text) == 1:
				_speakSingleCharSelected(text, locale, priority=priority)
			else:
				speech.speakTextSelected(text, priority=priority)

	if speakUnselected:
		if not generalize:
			for text in unselectedTextList:
				if len(text) == 1:
					_speakSingleCharUnselected(text, locale, priority=priority)
				else:
					# Translators: This is spoken to indicate what has been unselected.
					speech.speakSelectionMessage(_("%s unselected"), text, priority=priority)
		elif len(unselectedTextList) > 0:
			if not newInfo.isCollapsed:
				text = newInfo.text
				if len(text) == 1:
					_speakSingleCharUnselected(text, locale, priority=priority)
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
