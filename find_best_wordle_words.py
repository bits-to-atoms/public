# Copyright (c) 2022 Bits-To-Atoms contributors and others
# 
# https://github.com/bits-to-atoms
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import random

_INPUT_FILE  = 'words5.txt'
_OUTPUT_FILE = 'results.txt'
# At least 1 character must be here. Must be sorted.
_UNWANTED_LETTERS = ['q']
_MAX_VARIRANTS_IN_ROUND = [10, 10, 10, 10, 100]

def read_words(file_name):
  with open(file_name) as word_file:
    words = list(word_file.read().split())
    return words

# Returns at or before position (as for insert).
def find_before_pos(sorted_list, x):
  for i in range(len(sorted_list)):
    if x <= sorted_list[i]:
      return i
  return len(sorted_list)

# a is lowest bit and skip q.
def word_to_bits(word):
  bits = 0
  # The max number of overlapping letters or bits is (len(_UNWANTED_LETTERS) - 1).
  # So if we ignore just 1 letter, 0 overlapping bits are allowed. If we ignore
  # 2 letters, then we allow 1 overlapping letter, and the number of bits
  # covered must be no less than 5 - 1.
  if len(set(word)) < 5 - (len(_UNWANTED_LETTERS) - 1):
    return 0
  for c in word:
    # return 0 for invalid words, i.e., containing q.
    if c in _UNWANTED_LETTERS:
      return 0
    bits |= (0b1 << (ord(c) - (find_before_pos(_UNWANTED_LETTERS, c) + 97)))
  return bits

def print_one_state(words, si, s):
  print(hex(si), [words[wi] for wi in s[1]])
  for v_wi_list in s[2]:
    print(' =', [words[wi] for wi in v_wi_list])

def print_sample_states(words, states):
  si_longest = 0
  count_longest = 0
  for si in range(len(states)):
    slen = len(states[si][1])
    if slen == 0:
      continue
    # Print all sequences of length 5.
    if slen >= 5:
      print_one_state(words, si, states[si])

    # Reservoir sampling to keep one of the longest.
    if slen > len(states[si_longest][1]):
      si_longest = si
      count_longest == 1
    elif slen == len(states[si_longest][1]):
      if random.randint(0, count_longest) == 0:
        si_longest = si
      count_longest += 1
  
  # Print one sample of the longest sequences if less than 5.
  if len(states[si_longest][1]) < 5:
    print_one_state(words, si_longest, states[si_longest])

def choose_n(n, wis):
  result = [([], 0)]
  for i in range(n):
    new_result = []
    for ri in result:
      for k in range(ri[1], len(wis)):
        new_result.append((ri[0] + [wis[k]], k + 1))
    result = new_result
    if i == n - 1:
      return [ri[0] for ri in result]
  return []

def get_variants(states, bitwords, wis):
  ss = 0
  for wi in wis:
    ss |= bitwords[wi]
  return states[ss][2]

def save_one_state(words, s, states, bitwords, f):
  f.write('%s\n' % ' '.join(words[wi] for wi in s[1]))
  if len(s[1]) >= 5:
    for i in reversed(range(5)):
      wi_lists = choose_n(i + 1, s[1])
      for wis in wi_lists:
        lv = get_variants(states, bitwords, wis)
        for v in lv:
          f.write('- %s = %s\n' % (', '.join(words[wi] for wi in wis), ', '.join(words[wi] for wi in v)))

def save_states(words, states, bitwords, file_name):
  has_5 = False
  with open(file_name, 'w') as f:
    for s in states:
      if len(s[1]) >= 5:
        save_one_state(words, s, states, bitwords, f)
        has_5 = True
    if not has_5:
      for s in states:
        if len(s[1]) == 4:
          save_one_state(words, s, states, bitwords, f)

# n <= 2^25.
def one_bit_count(n):
  i = 1
  sum = 0
  # 33554432 = 2^25.
  while i <= 33554432:
    sum += (1 if (n & i) else 0)
    i <<= 1
  return sum

# Tries a word as the next round word, round > 0, as the 0th round was handled in
# the caller.
# si = state index = current sequence with bits representing letters covered.
# returns the new state if not 0.
def try_word_state(wi, bw, si, s):
  if bw == 0:
    return 0

  # This function handles only the next round, not the 0th, which must be handled
  # by the caller. If no 0th round word yet, bail; this function shouldn't have been
  # called.
  if s[0] == 0:
    return 0

  # We've already considered the current word.
  if s[0] > wi:
    return 0

  # This state is already good, complete with 5 words.
  if len(s[1]) >= 5:
    return 0

  # The max number of overlapping letters or bits is (_UNWANTED_LETTERS - 1).
  # So if we ignore just 1 letter, 0 overlapping bits are allowed and we must
  # have covered as many bits as 5 * rounds_so_far, or 5 * (len(s[1]) + 1 for this one).
  # If we ignore 2 letters, then we allow 1 overlapping letter, and the number of bits
  # covered so far must be no less than 5 * (len(s[1]) + 1) - 1.
  # Unwanted  1 |  2 |  3 |
  # Round 0:  5 |  4 |  3 |
  # Round 1: 10 |  9 |  8 |
  # Round 2: 15 | 14 | 13 |
  # Round 3: 20 | 19 | 18 |
  # Round 4: 25 | 24 | 23 |
  # Round 5: 30 | 29 | 28 |
  if one_bit_count(si | bw) < 5 * (len(s[1]) + 1) - (len(_UNWANTED_LETTERS) - 1):
    return 0
  # TODO: for the same state, we can still have different lengths of sequences?

  return si | bw

# wi = word index in vocabulary.
# bitword = binary using 25 bits, 0th bit being 'a'.
def try_word(wi, bitword, states):
  if bitword == 0:
    return

  # Try this word as the 0th round.
  s = states[bitword]
  # Another earlier word has the same letters; this one is a permutation.
  # So skip this word in favor of the previous occurrence.
  if s[0] > 0:
    if len(s[2]) >= _MAX_VARIRANTS_IN_ROUND[0]:
      return
    # Memorize as a variant.
    s[2].append([wi])
    return
  s[0] = wi + 1
  s[1].append(wi)

  # Try this word as non-0th round.
  for si in range(len(states)):
    new_si = try_word_state(wi, bitword, si, states[si])
    if new_si == 0:
      continue
    # The outer loop will not update this updated state entry due to the next
    # word index check in try_word_state.
    s = states[new_si]
    # Another earlier sequence has the same letters; this new combination is a permutation.
    if s[0] > 0:
      r = len(s[1]) - 1
      if len(s[2]) < _MAX_VARIRANTS_IN_ROUND[r]:
        # Memorize the would-be sequence as a full sequence variant for this state.
        s[2].append(states[si][1] + [wi])
      continue
    # Increment the minimum future work index to avoid retrying the current word again here.
    s[0] = wi + 1
    # Create the full sequence for this state.
    for wi0 in states[si][1]:
      s[1].append(wi0)
    s[1].append(wi)

if __name__ == '__main__':
  words = read_words(_INPUT_FILE)
  bitwords = [word_to_bits(w) for w in words]
  states = []
  # Use a loop to initialize to ensure elements point to different instances.
  for i in range(32 * 1024 * 1024):
    # [next_round_min_word_index, word_index_list, variant_list]
    states.append([0, [], []])
  for wi in range(len(bitwords)):
    if wi % 10 == 0:
      print('Processing', wi, words[wi], hex(bitwords[wi]))
    try_word(wi, bitwords[wi], states)
    if wi % 100 == 0:
      print_sample_states(words, states)

  print_sample_states(words, states)
  save_states(words, states, bitwords, _OUTPUT_FILE)