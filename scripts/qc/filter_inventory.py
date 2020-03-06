"""
Quickly subset Redcap inventories.
"""

import argparse
import pandas as pd
import sys
# import sibispy


def probably_not_missing_but_unmarked(inventory):
    # -> Site should confirm that hits can be automatically marked "not missing"
    return (inventory['non_nan_count'] > 0) & (inventory['missing'].isnull())


def probably_missing_but_marked_present(inventory):
    # -> Site should investigate why the form was marked "not missing"
    return (inventory['non_nan_count'] == 0) & (inventory['missing'] == 0)


def probably_missing_but_unmarked(inventory):
    # -> Site should confirm that hits can be automatically marked "missing"
    return (inventory['non_nan_count'] == 0) & inventory['missing'].isnull()


def content_not_marked_complete(inventory):
    # -> Site should confirm that hits can be automatically marked "complete"
    return (inventory['non_nan_count'] > 0) & (inventory['complete'] < 2)


def missing_not_marked_complete(inventory):
    # -> Site should confirm that hits can be automatically marked "complete"
    return (inventory['missing'] == 1) & (inventory['complete'] < 2)


def less_content_than_max(inventory):
    # -> Site should ensure that no content was omitted
    # (only makes sense on some forms)
    return ((inventory['non_nan_count'] > 0) &
            (inventory['non_nan_count'] < inventory['non_nan_count'].max()))


def has_content_but_marked_missing(inventory):
    # -> Missingness likely applied by mistake, should be switched to present
    return ((inventory['missing'] == 1) & (inventory['non_nan_count'] > 0))


def empty_and_not_complete(inventory):
    # Useful only prior to data release - for marking all empties complete
    return ((inventory['non_nan_count'] == 0) & (inventory['complete'] != 2))


def empty_and_not_ignored(inventory):
    # Cases that might just not have been filled in
    return ((inventory['non_nan_count'] == 0) & (inventory['exclude'] != 1))


def get_filter_results(inventorized_data, filter_function, verbose=False):
    """
    Apply pd.Index-returning function to data and return it filtered.
    """
    try:
        index = filter_function(inventorized_data)
    except KeyError as e:
        if verbose:
            print(e)
        return None
    else:
        return inventorized_data.loc[index]


def parse_args(filter_choices, input_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Verbose operation",
                        action="store_true")
    parser.add_argument("-p", "--post-to-github",
                        help="Post all issues to GitHub instead of stdout.",
                        action="store_true")
    parser.add_argument("-i", "--input",
                        help="Inventory file to operate on",
                        nargs='+',
                        required=True)
    parser.add_argument('-o', '--output',
                        help="File to save filtered inventory to",
                        default=sys.stdout)
    # Reference to `choices` in `help` courtesy of https://stackoverflow.com/a/20335589
    parser.add_argument('filter', metavar='FILTER', choices=filter_choices,
            help="Filter function to apply, one of following: {%(choices)s}")
    args = parser.parse_args(input_args)
    return args


if __name__ == '__main__':
    # TODO: There should be some way to auto-generate this - maybe embed the
    # filters in a file, import it, then get the names of all callables?
    FILTER_LIST = [
            probably_not_missing_but_unmarked,
            probably_missing_but_marked_present,
            probably_missing_but_unmarked,
            content_not_marked_complete,
            missing_not_marked_complete,
            less_content_than_max,
            has_content_but_marked_missing,
            empty_and_not_complete,
            empty_and_not_ignored,
    ]
    FILTERS = {x.__name__: x for x in FILTER_LIST}
    

    args = parse_args(FILTERS.keys())

    # TODO: Should explicitly assume + read in columns?
    all_out = []
    for filename in args.input:
        data = pd.read_csv(filename)
        filter_function = FILTERS[args.filter]
        result = get_filter_results(data, filter_function, verbose=args.verbose)
        if result is None:
            if args.verbose:
                print("Filter {} failed on file {}".format(args.filter, filename))
            sys.exit(1)
        elif not result.empty:
            all_out.append(result)

            if args.verbose:
                if args.output == sys.stdout:
                    output_display_name = "stdout"
                else:
                    output_display_name = args.output

                print("Filter {} used on {} => {}".format(args.filter, filename, output_display_name))
        else:
            if args.verbose:
                print("Filter {} used on {} => no matches, skipping.".format(args.filter, filename))
        
    (pd.concat(all_out, sort=False)
     .to_csv(args.output, index=False, float_format="%.0f"))
    sys.exit(0)
