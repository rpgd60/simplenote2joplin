from __future__ import print_function
import argparse
import json
import datetime
import logging
import sys
import re

def eprint(*args, **kwargs):
    """
    Print to stderr

    Placeholder until implementing proper logging

    Parameters
    ----------
    args
    kwargs
    """
    print(*args, file=sys.stderr, **kwargs)


class SimpleNoteToEnex:
    """
    Class to convert notes from Simple Note (in JSON format) to ENEX (Evernote Export) xml-based format.

    Simple Note (www.simplenote.com) is a popular note taking application. It exports notes in JSON format
    ENEX is the EverNote xml-based import/export format for notes, used by many note-taking applications.
    See: https://evernote.com/blog/how-evernotes-xml-export-format-works/
    Joplin is another (free and open source) multi platform note taking app that can import notes in ENEX format.

    Attributes
    ----------
    author : str
        author of the note.
    add_note_title : bool
        True if title of the note must be inferred from first line of the (Simple Note) note
    sn_title_separator : str
        Separates first line from the rest in SN Notes - used to identify title.  Initially hard-coded to '\r\n'
    json_file : str
        The JSON file containing one or multiple Simple Note notes
    export_time : str
        Time at which the converted Notes were created.  Use for all notes the time of execution of class __init__
    max_notes: int
        Maximum number of notes to be converted.  Used mainly for tests and debugging (e.g. find offending note)
    filter_tags: bool
        True if a tag_filter will be used. False otherwise
    tag_filter: str or str[]
        Set of tags used to filter subset of notes to be converted (e.g. ['recipes', 'cooking'])
        If a tag_filter is applied, all untagged notes will also be excluded.
    match_tagged: bool
        if True,  convert only notes with tags
    match_untagged: bool
        if True, convert only notes without tags
    invert_match : bool
        if True,  invert the result of matching tag_filter OR match_untagged OR match_tagged
    line_sep: str
        Line separator to prettify the generated XML.  Hard coded to '\r\n'
        TODO: verify if conversion also works with blank (empty string) separator
    verbose : bool
        generage verbose output to stderr
        TODO: implement proper logging

    Methods
    -------
    convert_to_enex(sn_note)
        Convert an individual Simple Note note in JSON format to ENEX XML
    process_file()
        Process all notes in Simple Note export file. Call convert_to_enex for notes allowed by tag_filter
    match_note_logical_or()
        Determine if a given note should be converted based on tag filter or match tagged/untagged flags

    """

    def __init__(self, json_file, author=None, create_title=False, verbose_level=0, max_notes=None, tag_filter='',
                 invert_match=False, match_tagged=False, match_untagged=False):
        """

        Parameters
        ----------
        json_file
        author
        create_title
        verbose_level
        max_notes
        tag_filter
        invert_match
        match_tagged
        match_untagged

        """
        self.author = author
        self.add_note_title = create_title
        # Max length -- in case there is no \r\n to delimit the note's first line
        self.max_title_len = 30   # Still unused
        self.sn_title_separator = '\r\n'
        self.json_file = json_file
        self.export_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S%ZZ")  # TODO: fix time format (Z)
        self.verbose_level = verbose_level
        self.match_tagged = match_tagged
        self.match_untagged = match_untagged
        self.invert_match = invert_match
        if max_notes == None:
            self.max_notes = sys.maxsize
        else:
            self.max_notes = max_notes
        if tag_filter is None or tag_filter == '':
            self.filter_tags = False
        else:
            self.filter_tags = True
            self.tag_filter = tag_filter.split(',')
        self.match_untagged = match_untagged
        self.match_tagged = match_tagged
        self.line_sep = '\r\n'
        if self.verbose_level > 1:
            eprint(f"match_untagged {self.match_untagged}")
            eprint(f"match_tagged {self.match_tagged}")
            eprint(f"filter_tags {self.filter_tags}")
            eprint(f"invert_match {self.invert_match}")
    
    def cleanup_content(self, json_content, pattern = "\\r\\n", remove_whitespace = True):
        """
        Clean up json_content from simplenotes (or other note provider):
        - remove leading and trailing whitespace - driven by remove_whitespace Boolean
        - remove leading and training pattern strings (default '\r\n' -> empty lines) 
        
        returns:  "clean" string
        """
        if remove_whitespace:
            # Leading whitespace
            #temp_string = re.sub("\A\s+", "", json_content)
            # Trailing whitespace
            #temp_string = re.sub("\s+\Z", "", temp_string)
            temp_string = json_content.strip()

        # remove pattern at the start of the string
        temp_string = re.sub("\A" + pattern, "", temp_string)
        # remove pattern at the end of the string 
        temp_string = re.sub(pattern + "\Z", "", temp_string)
        return temp_string

    def convert_to_enex(self, sn_note):
        """
        Convert individual Simple Note from JSON to ENEX format, adding some fields like author if requested

        Parameters
        ----------
        sn_note: dict
            Simple Note note converted from JSON into dict
        Returns
        -------
        str
            full text (XML format) of Simple Note note converted to XML
        """
        # Lambda to simplify verification of parameter and convert None to empty string ''
        verif_none = lambda note_property: note_property or ''
        # Simple Note export formats date as YYYY-MM-DDT:hh:mm:ss.xxxZ
        # ENEX seems to use YYYYMMDDThhmmssZ
        # Perform basic conversion keeping the milliseconds (xxx) anyway
        enex_created = sn_note['creationDate'].replace('-', '').replace(':', '').replace('.', '')
        enex_updated = sn_note['lastModified'].replace('-', '').replace(':', '').replace('.', '')
        enex_content = verif_none(sn_note['content'])
        enex_content = self.cleanup_content(enex_content, self.line_sep, True)
        enex_author = verif_none(self.author)
        enex_source = "Converted from Simple Note (simplenote.com)"
        # enex_latitude = kwargs['latitude']
        # enex_longitude = kwargs['longitude']
        # enex_altitude = kwargs['altitude']

        if (self.add_note_title):
            # Simple Note JSON export format does not have explicit field to contain the note title.
            # Assume title is first line of Simple Note content, delimited by first "\r\n"
            enex_title = enex_content.split(self.sn_title_separator, 1)[0]
        else:
            enex_title = ''

        enex_tags = ''
        if 'tags' in sn_note:
            for tag in sn_note['tags']:
                enex_tags += '<tag>' + tag + '</tag>' + self.line_sep
        # Build XML output using f-strings
        # TODO: verify if the CDATA and DOCTYPE are needed for plain Markdown Notes.
        enex_note = f'''
<note>
<title>{enex_title}</title>
<content>
    <![CDATA[<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
    <en-note>
       {enex_content} 
    </en-note>
    ]]>
</content>
<created>{enex_created}</created>
<updated>{enex_updated}</updated>
<note-attributes>
    <author>{enex_author}</author>
</note-attributes>
{enex_tags}
</note>
        '''
        return enex_note + self.line_sep

    #          <source>{enex_source}</source>
    #          <reminder-order>0</reminder-order>

    def process_file(self):
        """
        Process JSON file (self.json_file) with Simple Note notes in JSON format

        Returns
        -------
        str
            full text of json_file converted to ENEX format (XML)

        """

        #    </en-export export-date=\"{export_time}\">
        enex_file_header = f'''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-export SYSTEM "http://xml.evernote.com/pub/evernote-export3.dtd">
<en-export export-date=\"{self.export_time}\">
'''
        enex_file_footer = '''</en-export>'''
        enex_text = ''
        with open(self.json_file) as jfp:
            simplenotes = json.load(jfp)
            num_active_notes = len(simplenotes['activeNotes'])
            if self.verbose_level >= 1:
                eprint(f"Processing file: {self.json_file} ")
                eprint(f"Notes author: ", self.author)
                eprint(f"Active notes:   {num_active_notes}")
                if 'trashedNotes' in simplenotes:
                    eprint(f"Trashed notes:  {len(simplenotes['trashedNotes'])} -- will not be converted to ENEX")
            nconv = 0
            number_to_be_converted = min(self.max_notes, num_active_notes)
            for sn_note in simplenotes['activeNotes']:
                if nconv >= number_to_be_converted:
                    break
                if self.match_note_logical_or(sn_note):
                    enex_text += self.convert_to_enex(sn_note)
                    nconv += 1
        if self.verbose_level > 0:
            eprint(f"Converted {nconv} notes")
        return enex_file_header + self.line_sep + enex_text + self.line_sep + enex_file_footer

    def match_note_logical_or(self, sn_note):
        """
        Function to implement the logic to filter by tags or tag presence/absence when deciding
        if a given note is to be converted.

        The logic to filter by  tags is
        - tag filtering is case sensitive (following the behavior of  "tag:" search in Simple Note)
        - match  if at least one tag in the filter is present among the tags of the note.
        - example:  if the filter (self.tag_filter) is ['linux', 'windows'] and the tags in the note contain
          ['Mac','linux'],  the note will be converted.

        The chosen logic for different tag filters is:
        - If no filters are selected (default) - return True  (by default, all notes are converted)
        - Otherwise  return the logical OR of all applied filters,  XORing the result of the OR with self.invert_match

        This allows some valid but strange behavior combinations depending of selected filter flags.
        For example:
          - combining  --match-tagged and --match-untagged  converts all tags (equivalent to specifying no match/filter)
          - combining  --tag-filter 'linux,windows' --match-untagged converts all untagged notes and all tagged notes with tags containing 'linux' and/or 'windows'
          - combining  --tag-filter 'foo'  and --match-tagged converts all tagged notes regardless of the tag
          - combining  --match-tagged and --invert-match  is the same as --match-untagged

        When in doubt, it is simpler to use a single filter expression (--tag-filter, --match-tagged, --match-untagged)
        possibly complemented with --invert-match

        Parameters
        ----------
        sn_note : dict
            Simple Note note being evaluated - dict from original individual note formatted as json.
            Should contain as dict element an array of tags (sn_note['tags'])
        Returns
        -------
            bool
            Result of applying all active filters, XORed with invert_match

        """
        # if no filter or matching command is applied
        if not(self.filter_tags or self.match_tagged or self.match_untagged):
            return True         # regardless of value of invert_match
        convert_this_note = False
        if self.filter_tags and 'tags' in sn_note:
            # Convert array of tags in filter and array of tags in note into sets.
            # Match if the intersection of both sets is non-empty.
            if len(set(self.tag_filter) & (set(sn_note['tags']))) != 0:
                convert_this_note = True
        if self.match_untagged and not('tags' in sn_note):
            convert_this_note = True
        if self.match_tagged and 'tags' in sn_note:
            convert_this_note = True
        # XOR result with invert_match
        return convert_this_note != self.invert_match


def main(args):
    # TODO: explicit argument for output file
    sne = SimpleNoteToEnex(args.json_file, args.author, args.create_title, \
                           args.verbose_level, args.num_notes, args.tag_filter, args.invert_match,
                           args.match_tagged, args.match_untagged )
    enex_file = sne.process_file()
    print(enex_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--json-file', required=True, type=str, dest='json_file',
                        help='Simple Note export file (json) to be converted to ENEX')
    parser.add_argument('--author', required=False, type=str,
                        help='Specify an author for all converted notes')
    parser.add_argument('--create-title', required=False, dest='create_title', action='store_true',
                        help='Attempt to create a title for each ENEX note from first line of "Simple Note" notes')
    parser.add_argument('--tag-filter', required=False, dest='tag_filter',
                        help='Comma-separated list of tags. Will convert notes matching any tag in list')
    parser.add_argument('--match-tagged', required=False, dest='match_tagged', action='store_true',
                        help='Convert tagged notes')
    parser.add_argument('--match-untagged', required=False, dest='match_untagged', action='store_true',
                        help='Convert untagged notes')
    parser.add_argument('--invert-match', required=False, dest='invert_match', action='store_true',
                        help='Invert match after combining (OR) all other filters/matching conditions')
    parser.add_argument('--verbose-level', required=False, dest='verbose_level', type=int, default='0',
                        help=f"Verbose output level. Output to stderr. Default 0 - no output")
    parser.add_argument('--number', required=False, dest='num_notes', type=int,
                        help='Number of notes to convert (Optional, default is convert all notes)')
    args = parser.parse_args()
    main(args)
