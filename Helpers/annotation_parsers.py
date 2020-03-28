from xml.etree import ElementTree
from time import perf_counter
import pandas as pd
import json
import os
from visual_tools import visualization_wrapper


def get_tree_item(parent, tag, file_path, find_all=False):
    """
    Get item from xml tree element.
    Args:
        parent: Parent in xml element tree
        tag: tag to look for.
        file_path: Current xml file being handled.
        find_all: If True, all elements found will be returned.

    Return:
        Tag item.
    """
    target = parent.find(tag)
    if find_all:
        target = parent.findall(tag)
    if target is None:
        raise ValueError(f'Could not find "{tag}" in {file_path}')
    return target


def parse_voc_file(file_path, voc_conf):
    """
    Parse voc annotation from xml file.
    Args:
        file_path: Path to xml file.
        voc_conf: voc configuration file.

    Return:
        A list of image annotations.
    """
    assert os.path.exists(file_path)
    image_data = []
    with open(voc_conf) as json_data:
        tags = json.load(json_data)
    tree = ElementTree.parse(file_path)
    image_path = get_tree_item(tree, tags['Tree']['Path'], file_path).text
    size_item = get_tree_item(tree, tags['Size']['Size Tag'], file_path)
    image_width = get_tree_item(size_item, tags['Size']['Width'], file_path).text
    image_height = get_tree_item(size_item, tags['Size']['Height'], file_path).text
    for item in get_tree_item(tree, tags['Object']['Object Tag'], file_path, True):
        name = get_tree_item(item, tags['Object']['Object Name'], file_path).text
        box_item = get_tree_item(item, tags['Object']['Object Box']['Object Box Tag'], file_path)
        x0 = get_tree_item(box_item, tags['Object']['Object Box']['X0'], file_path).text
        y0 = get_tree_item(box_item, tags['Object']['Object Box']['Y0'], file_path).text
        x1 = get_tree_item(box_item, tags['Object']['Object Box']['X1'], file_path).text
        y1 = get_tree_item(box_item, tags['Object']['Object Box']['Y1'], file_path).text
        image_data.append([image_path, name, image_width, image_height, x0, y0, x1, y1])
    return image_data


def adjust_frame(frame, cache_file):
    """
    Add relative width, relative height and object ids to annotation pandas DataFrame.
    Args:
        frame: pandas DataFrame containing annotation data.
        cache_file: cache_file: csv file name containing current session labels.

    Return:
        Frame with the new columns
    """
    object_id = 1
    for item in frame.columns[2:]:
        frame[item] = frame[item].astype(float).astype(int)
    frame['Relative Width'] = (frame['X_max'] - frame['X_min']) / frame['Image Width']
    frame['Relative Height'] = (frame['Y_max'] - frame['Y_min']) / frame['Image Height']
    for object_name in list(frame['Object Name'].drop_duplicates()):
        frame.loc[frame['Object Name'] == object_name, 'Object ID'] = object_id
        object_id += 1
    frame.to_csv(os.path.join('..', 'Caches', cache_file), index=False)
    print(f'Parsed labels:\n{frame["Object Name"].value_counts()}')
    return frame


@visualization_wrapper
def parse_voc_folder(folder_path, voc_conf, cache_file='data_set_labels.csv'):
    """
    Parse a folder containing voc xml annotation files.
    Args:
        folder_path: Folder containing voc xml annotation files.
        voc_conf: Path to voc json configuration file.
        cache_file: csv file name containing current session labels.

    Return:
        pandas DataFrame with the annotations.
    """
    assert os.path.exists(folder_path)
    cache_path = os.path.join('..', 'Caches', cache_file)
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)
    image_data = []
    frame_columns = [
        'Image Path', 'Object Name', 'Image Width', 'Image Height', 'X_min', 'Y_min', 'X_max', 'Y_max']
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.xml'):
            annotation_path = os.path.join(folder_path, file_name)
            image_labels = parse_voc_file(annotation_path, voc_conf)
            image_data.extend(image_labels)
    frame = pd.DataFrame(image_data, columns=frame_columns)
    if frame.empty:
        raise ValueError(f'No labels were found in {os.path.abspath(folder_path)}')
    frame = adjust_frame(frame, cache_file)
    return frame


if __name__ == '__main__':
    t1 = perf_counter()
    fr = parse_voc_folder('../../../beverly_hills_gcp/lbl', '../Config/voc_conf.json')
    print(fr)
    print(f'Time: {perf_counter() - t1} seconds')
