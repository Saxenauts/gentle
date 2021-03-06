import difflib
import json
import os
import sys

import metasentence
import language_model
import standard_kaldi

# TODO(maxhawkins): try using the (apparently-superior) time-mediated dynamic
# programming algorithm used in sclite's alignment process:
# http://www1.icsi.berkeley.edu/Speech/docs/sctk-1.2/sclite.htm#time-mediated
def align(alignment, ms):
    '''Use the diff algorithm to align the raw tokens recognized by Kaldi
    to the words in the transcript (tokenized by MetaSentence).
    
    The output combines information about the timing and alignment of
    correctly-aligned words as well as words that Kaldi failed to recognize
    and extra words not found in the original transcript.
    '''
    hypothesis = [X["word"] for X in alignment]
    reference = ms.get_kaldi_sequence()

    display_seq = ms.get_display_sequence()
    txt_offsets = ms.get_text_offsets()

    out = []
    for op, a, b in word_diff(hypothesis, reference):

        if op == 'delete':
            continue

        display_word = display_seq[b]
        start_offset, end_offset = txt_offsets[b]

        if op == 'equal':
            hyp_word = hypothesis[a]
            hyp_token = alignment[a]
            phones = hyp_token.get("phones", [])
            start = hyp_token["start"]
            end = hyp_token["start"] + hyp_token["duration"]

            out.append({
                "case": "success",
                "startOffset": start_offset,
                "endOffset": end_offset,
                "word": display_word,
                "alignedWord": hyp_word,
                "phones": phones,
                "start": start,
                "end": end,
            })
        elif op in ['insert', 'replace']:
            out.append({
                "case": "not-found-in-audio",
                "startOffset": start_offset,
                "endOffset": end_offset,
                "word": display_word,
            })
    return out

def word_diff(a, b):
    '''Like difflib.SequenceMatcher but it only compares one word
    at a time. Returns an iterator whose elements are like
    (operation, index in a, index in b)'''
    matcher = difflib.SequenceMatcher(a=a, b=b)
    for op, a_idx, _, b_idx, _ in by_word(matcher.get_opcodes()):
        yield (op, a_idx, b_idx)

def by_word(opcodes):
    '''Take difflib.SequenceMatcher.get_opcodes() output and
    return an equivalent opcode sequence that only modifies
    one word at a time'''
    for op, s1, e1, s2, e2 in opcodes:
        if op == 'delete':
            for i in range(s1, e1):
                yield (op, i, i+1, s2, s2)
        elif op == 'insert':
            for i in range(s2, e2):
                yield (op, s1, s1, i, i+1)
        else:
            for i1, i2 in zip(range(s1, e1), range(s2, e2)):
                yield (op, i1, i1 + 1, i2, i2 + 1)

if __name__=='__main__':
    TEXT_FILE = sys.argv[1]
    JSON_FILE = sys.argv[2]
    OUTPUT_FILE = sys.argv[3]

    with open('data/graph/words.txt') as f:
        vocab = metasentence.load_vocabulary(f)

    ms = metasentence.MetaSentence(open(TEXT_FILE).read(), vocab)
    alignment = json.load(open(JSON_FILE))['words']

    out = align(alignment, ms)
    
    json.dump(out, open(OUTPUT_FILE, 'w'), indent=2)
