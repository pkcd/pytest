import sys
import xml.etree.ElementTree as ElementTree
import time
import os
import random


class Constants:
    def __init__(self):
        pass

    ELEMENT = 'element'

    COMPLEX_TYPE = 'complexType'
    SIMPLE_TYPE = 'simpleType'
    COMPLEX_CONTENT = 'complexContent'
    SIMPLE_CONTENT = 'simpleContent'
    RESTRICTION = 'restriction'
    EXTENSION = 'extension'
    ENUMERATION = 'enumeration'
    LIST = 'list'
    UNION = 'union'
    ATTRIBUTE_GROUP = 'attributeGroup'
    ATTRIBUTE = 'attribute'

    GROUP = 'group'
    ALL = 'all'
    CHOICE = 'choice'
    SEQUENCE = 'sequence'

    NAME = 'name'
    TYPE = 'type'
    REF = 'ref'
    BASE = 'base'
    VALUE = 'value'
    MIXED = 'mixed'
    MIN_OCCURS = 'minOccurs'
    MAX_OCCURS = 'maxOccurs'

    INCLUDE = 'include'
    SCHEMA_LOCATION = 'schemaLocation'


class SVGParser:
    _parsed_xsd = None
    _namespace_prefix = None
    _element_types = None
    _unbounded_size = None
    _attribute_group_elements = None
    _group_elements = None
    _type_name_to_element = None

    def _replace_includes(self, already_replaced):
        root = self._parsed_xsd.getroot()
        include_processed = False
        for an_include in root.findall(self._add_prefix(Constants.INCLUDE)):
            include_processed = True
            schema_location = an_include.get(Constants.SCHEMA_LOCATION)
            if not (schema_location in already_replaced):
                root.extend(ElementTree.parse(schema_location).getroot().findall('./'))
                already_replaced[schema_location] = True
            root.remove(an_include)
        if include_processed:
            self._replace_includes(already_replaced)

    def __init__(self, path):
        self._parsed_xsd = ElementTree.parse(path)
        root_name = self._parsed_xsd.getroot().tag
        self._namespace_prefix = root_name[root_name.find("{"): root_name.find("}") + 1]
        self._replace_includes(dict())
        self._element_types = dict()
        self._attribute_group_elements = dict()
        self._group_elements = dict()
        #Create type dictionary key -> type_name without namespace prefix; value-> type_element as in svg xml
        self._type_name_to_element = dict()
        for elem in self._parsed_xsd.iter():
            elem_name = elem.get(Constants.NAME)
            if elem_name is None:
                continue
            if elem.tag == self._add_prefix(Constants.SIMPLE_TYPE) \
                    or elem.tag == self._add_prefix(Constants.COMPLEX_TYPE):
                self._type_name_to_element[elem_name] = elem
            if elem.tag == self._add_prefix(Constants.ATTRIBUTE_GROUP):
                self._attribute_group_elements[elem_name] = elem
            if elem.tag == self._add_prefix(Constants.GROUP):
                self._group_elements[elem_name] = elem

        for elem in self._parsed_xsd.iter(self._add_prefix(Constants.ELEMENT)):
            type_name = elem.get(Constants.TYPE)
            type_xsd_node = None
            if type_name is not None:
                type_name_without_prefix = type_name[type_name.find(":") + 1:]
                if type_name_without_prefix in self._type_name_to_element:
                    type_xsd_node = self._type_name_to_element[type_name_without_prefix]
                else:
                    #mostly xs:string, xs:integer or some primitive type
                    type_xsd_node = type_name
            elif elem.find(self._add_prefix(Constants.COMPLEX_TYPE)) is not None:
                type_xsd_node = elem.find(self._add_prefix(Constants.COMPLEX_TYPE))
            elif elem.find(self._add_prefix(Constants.SIMPLE_TYPE)) is not None:
                type_xsd_node = elem.find(self._add_prefix(Constants.SIMPLE_TYPE))
            self._element_types[elem.get(Constants.NAME)] = type_xsd_node

        self._unbounded_size = 3

    def get_target_namespace(self):
        """
        @return: string, targetNamespace attribute of schema element
        """
        return self._parsed_xsd.getroot().get('targetNamespace')

    def get_child_names(self, parent_name, max_num):
        """
        @parent: string, tag of parent element
        @max_num: int, hint number to keep the length of the list below this number
        @return: ( [ ([element|data], string) ], {"name":"value"} ), a possible sequence of member names and attributes
            for this type. The member can be an element or data and is indicated by the first component of the tuple
        """

        return self._get_element_names(self._element_types[parent_name], max_num)

    def _get_attributes(self, attribute_parent_node):
        """
        @attribute_parent_node: xsd node containing attribute nodes and attributeGroup nodes
        @return: dict, key-value pairs of attribute name and an associated random value
        """
        returned_attributed = self._get_attribute_values_from_immediate_nodes(attribute_parent_node)
        for attribute_group_ref in attribute_parent_node.findall(self._namespace_prefix + Constants.ATTRIBUTE_GROUP):
            attribute_group_name = attribute_group_ref.get(Constants.REF)
            if attribute_group_name is None or len(attribute_group_name) < 1:
                continue
            attribute_group_node = self._attribute_group_elements[self._strip_prefix(attribute_group_name)]
            more_attribute_values = self._get_attribute_values_from_immediate_nodes(attribute_group_node)
            returned_attributed = dict(returned_attributed.items() + more_attribute_values.items())
        return returned_attributed

    def _get_attribute_values_from_immediate_nodes(self, parent_node):
        returned_attributed = dict()
        for attribute_node in parent_node.findall(self._namespace_prefix + Constants.ATTRIBUTE):
            attribute_ref = attribute_node.get(Constants.REF)
            if attribute_ref is not None:
                (attribute_name, attribute_type) = self._get_attribute_from_ref(attribute_ref)
            else:
                attribute_name = attribute_node.get(Constants.NAME)
                attribute_type = attribute_node.get(Constants.TYPE)
            if attribute_name is not None and len(attribute_name) > 0:
                if attribute_type is None or len(attribute_type) < 1:
                    if attribute_node.find(self._add_prefix(Constants.SIMPLE_TYPE)) is not None:
                        attribute_type = attribute_name + "_syntheticType"
                        self._type_name_to_element[attribute_type] = attribute_node.find(
                            self._add_prefix(Constants.SIMPLE_TYPE))
                    else:
                        attribute_type = "xs:string"
                returned_attributed[attribute_name] = self._get_value_of_basic_type(attribute_type)
        return returned_attributed

    def _get_element_names(self, type_node_xsd, max_num):
        """
        @ type_node_xsd: xsd type node or string, in xsd schema. If string then assume basic type in xs namespace
        @max_num: int, hint number to keep the length of the list below this number
        @return: ( [ ([element|data], string) ], {"name":"value"} ), a possible sequence of member names and attributes
            for this type. The member can be an element or data and is indicated by the first component of the tuple
        """
        if type_node_xsd is None:
            return [], {}
        if isinstance(type_node_xsd, str):
            return [("data", self._get_value_of_basic_type(type_node_xsd))], {}
        elif type_node_xsd.tag == self._add_prefix(Constants.COMPLEX_TYPE):
            if type_node_xsd.find(self._add_prefix(Constants.SIMPLE_CONTENT)) is not None:
                (member_list, member_attr) = self._parse_simple_content(
                    type_node_xsd.find(self._add_prefix(Constants.SIMPLE_CONTENT)), max_num)
            elif type_node_xsd.find(self._add_prefix(Constants.COMPLEX_CONTENT)) is not None:
                (member_list, member_attr) = self._parse_complex_content(
                    type_node_xsd.find(self._add_prefix(Constants.COMPLEX_CONTENT)), max_num)
            else:
                (member_list, _) = self._parse_indicator(type_node_xsd, max_num)
                (member_list, member_attr) = member_list, self._get_attributes(type_node_xsd)
            is_mixed = type_node_xsd.get(Constants.MIXED)
            if is_mixed == "true":
                num_mixed = int(len(member_list) * 0.1) + 1
                for __ in range(num_mixed):
                    random_insert_point = 0
                    if len(member_list) > 0:
                        random_insert_point = random.randint(0, len(member_list) - 1)
                    member_list.insert(random_insert_point, ("data", self._get_value_of_basic_type("xs:string")))
            return member_list, member_attr
        elif type_node_xsd.tag == self._add_prefix(Constants.SIMPLE_TYPE):
            return self._parse_simple_type(type_node_xsd)
        else:
            return [], {}

    def _parse_complex_content(self, complex_content_node, max_num):
        if complex_content_node.find(self._add_prefix(Constants.RESTRICTION)) is not None:
            return self._parse_restriction_complex(complex_content_node.find(self._add_prefix(Constants.RESTRICTION)),
                                                   max_num)
        else:
            return self._parse_extension(complex_content_node.find(self._add_prefix(Constants.EXTENSION)), max_num)

    def _parse_restriction_complex(self, restriction_node, max_num):
        (member_list, _) = self._parse_indicator(restriction_node, max_num)
        return member_list, self._get_attributes(restriction_node)

    def _parse_simple_content(self, simple_content_node, max_num):
        """
         @return: ( [ ([element|data], string) ], {"name":"value"} ), return text according to restriction or extension
            specified there in
        """
        if simple_content_node.find(self._add_prefix(Constants.RESTRICTION)) is not None:
            return self._parse_restriction_simple(simple_content_node.find(self._add_prefix(Constants.RESTRICTION)))
        else:
            return self._parse_extension(simple_content_node.find(self._add_prefix(Constants.EXTENSION)), max_num)

    def _parse_extension(self, extension_node, max_num):
        """
         @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        base_type = extension_node.get(Constants.BASE)
        if self._strip_prefix(base_type) in self._type_name_to_element:
            base_type = self._type_name_to_element[self._strip_prefix(base_type)]
        (base_list, base_attributes) = self._get_element_names(base_type, max_num)
        (member_list, _) = self._parse_indicator(extension_node, max_num)
        return base_list + member_list, dict(base_attributes.items() + self._get_attributes(extension_node).items())

    def _parse_indicator(self, indicator_parent, max_num):
        """
        @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        if indicator_parent.find(self._add_prefix(Constants.CHOICE)) is not None:
            return self._parse_choice_indicator(indicator_parent.find(self._add_prefix(Constants.CHOICE)), max_num)
        elif indicator_parent.find(self._add_prefix(Constants.ALL)) is not None:
            return self._parse_all_indicator(indicator_parent.find(self._add_prefix(Constants.ALL)), max_num)
        elif indicator_parent.find(self._add_prefix(Constants.GROUP)) is not None:
            return self._parse_group_indicator(indicator_parent.find(self._add_prefix(Constants.GROUP)), max_num)
        elif indicator_parent.find(self._add_prefix(Constants.SEQUENCE)) is not None:
            return self._parse_sequence_indicator(indicator_parent.find(self._add_prefix(Constants.SEQUENCE)), max_num)
        return [], {}

    def _parse_all_indicator(self, all_node, max_num):
        """
        @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        return [], {}

    def _parse_group_indicator(self, group_node, max_num):
        """
        @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        group_ref = group_node.get(Constants.REF)
        if group_ref is not None:
            actual_group_node = self._group_elements[self._strip_prefix(group_ref)]
            if actual_group_node.find(self._add_prefix(Constants.CHOICE)) is not None:
                return self._parse_choice_indicator(actual_group_node.find(self._add_prefix(Constants.CHOICE)), max_num)
            elif actual_group_node.find(self._add_prefix(Constants.ALL)) is not None:
                return self._parse_all_indicator(actual_group_node.find(self._add_prefix(Constants.ALL)), max_num)
            elif actual_group_node.find(self._add_prefix(Constants.SEQUENCE)) is not None:
                return self._parse_sequence_indicator(actual_group_node.find(self._add_prefix(Constants.SEQUENCE)),
                                                      max_num)
        return [], {}

    def _parse_sequence_indicator(self, sequence_node, max_num):
        """
        @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        possible_children = []
        min_sequence_elements = self._get_min_or_max(sequence_node, True)
        #iterate over all children
        for a_member in sequence_node:
            if len(possible_children) >= max_num:
                break
            if a_member.tag == self._add_prefix(Constants.ELEMENT):
                an_element_name = self._get_elem_name(a_member)
                if an_element_name is not None and len(an_element_name) > 0:
                    possible_children.append((Constants.ELEMENT, an_element_name))
            elif a_member.tag == self._add_prefix(Constants.GROUP):
                (member_list, _) = self._parse_group_indicator(a_member, max_num - len(possible_children))
                possible_children.extend(member_list)
            elif a_member.tag == self._add_prefix(Constants.CHOICE):
                (member_list, _) = self._parse_choice_indicator(a_member, max_num - len(possible_children))
                possible_children.extend(member_list)
            elif a_member.tag == self._add_prefix(Constants.SEQUENCE):
                (member_list, _) = self._parse_sequence_indicator(a_member, max_num - len(possible_children))
                possible_children.extend(member_list)
        return possible_children, {}

    def _get_min_or_max(self, some_node, is_min):
        if is_min:
            attribute_name = Constants.MIN_OCCURS
        else:
            attribute_name = Constants.MAX_OCCURS
        attribute_value = some_node.get(attribute_name)
        if attribute_value is None:
            return 1
        elif self._is_int(attribute_value):
            return int(attribute_value)
        else:
            return self._unbounded_size

    def _parse_choice_indicator(self, choice_node, max_num):
        """
        @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        mandatory_elements = []
        #iterate over all children
        how_many_choices = random.randint(self._get_min_or_max(choice_node, True),
                                          self._get_min_or_max(choice_node, False))
        all_possible_choices = choice_node.findall('./')
        for __a_var in range(how_many_choices):
            a_choice = random.choice(all_possible_choices)
            num_repeat_this_choice = random.randint(self._get_min_or_max(a_choice, True),
                                                    self._get_min_or_max(a_choice, False))
            num_repeat_this_choice = min(num_repeat_this_choice, max_num - len(mandatory_elements))
            if a_choice.tag == self._add_prefix(Constants.ELEMENT):
                for i in range(num_repeat_this_choice):
                    an_elem_name = self._get_elem_name(a_choice)
                    if an_elem_name is not None and len(an_elem_name) > 0:
                        mandatory_elements.append((Constants.ELEMENT, an_elem_name))
            elif a_choice.tag == self._add_prefix(Constants.CHOICE):
                for i in range(num_repeat_this_choice):
                    (member_list, _) = self._parse_choice_indicator(a_choice, max_num - len(mandatory_elements))
                    mandatory_elements.extend(member_list)
            elif a_choice.tag == self._add_prefix(Constants.GROUP):
                for i in range(num_repeat_this_choice):
                    (member_list, _) = self._parse_group_indicator(a_choice, max_num - len(mandatory_elements))
                    mandatory_elements.extend(member_list)
            elif a_choice.tag == self._add_prefix(Constants.SEQUENCE):
                for i in range(num_repeat_this_choice):
                    (member_list, _) = self._parse_sequence_indicator(a_choice, max_num - len(mandatory_elements))
                    mandatory_elements.extend(member_list)

        return mandatory_elements, {}

    def _get_elem_name(self, element_node):
        elem_name = element_node.get(Constants.NAME)
        if elem_name is None:
            elem_ref = element_node.get(Constants.REF)
            if elem_ref is not None:
                elem_name = self._strip_prefix(elem_ref)
        if elem_name is not None:
            return elem_name
        return ""

    def _remove_list_element(self, l, index):
        return l[0:index] + l[index + 1:]

    def _parse_simple_type(self, type_node_xsd):
        """
        @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        if type_node_xsd.find(self._add_prefix(Constants.RESTRICTION)) is not None:
            return self._parse_restriction_simple(type_node_xsd.find(self._add_prefix(Constants.RESTRICTION)))
        elif type_node_xsd.find(self._add_prefix(Constants.LIST)) is not None:
            return [], {}
        elif type_node_xsd.find(self._add_prefix(Constants.UNION)) is not None:
            return [], {}
        return [], {}

    def _parse_restriction_simple(self, restriction_node):
        """
        @return: ( [ ([element|data], string) ], {"name":"value"} )
        """
        enumerations = restriction_node.findall(self._add_prefix(Constants.ENUMERATION))
        if len(enumerations) > 0:
            random_child = random.randint(0, len(enumerations) - 1)
            data_value = enumerations[random_child].get(Constants.VALUE)
        else:
            data_value = self._get_value_of_basic_type(restriction_node.get(Constants.BASE))
        return [("data", data_value)], {}

    def _get_min_max_occurs(self, elem):
        """
        @elem: xsd xml node containing attributed minOccurs and maxOccurss
        @return: a random integer between the range
        """
        min_occurs = elem.get('minOccurs')
        max_occurs = elem.get('maxOccurs')
        if min_occurs is None:
            min_occurs = 1
        if max_occurs is None:
            max_occurs = 1
        if max_occurs == "unbounded":
            max_occurs = self._unbounded_size
        return random.randint(int(min_occurs), int(max_occurs))

    def _get_value_of_basic_type(self, type_name):
        if type_name is None:
            return ""
        elif self._check_basic_type(type_name, ["string", "ID", "NMTOKEN", "NMTOKENS"]):
            return_string = ""
            for i in range(self._unbounded_size):
                return_string += chr(97 + random.choice(range(26)))
            return return_string
        elif self._check_basic_type(type_name, ["anyURI"]):
            return "http://www.google.com"
        elif self._check_basic_type(type_name, ["language"]):
            return "en"
        elif self._check_basic_type(type_name, ["integer", "positiveInteger", "nonNegativeInteger", "byte", "int",
                                                "long", "short", "unsignedLong", "unsignedInt", "unsignedShort",
                                                "unsignedByte"]):
            return str(random.randint(1, 5))
        elif self._check_basic_type(type_name, ["nonPositiveInteger", "negativeInteger"]):
            return str(-1 * random.randint(1, 5))
        elif self._check_basic_type(type_name, ["decimal"]):
            return str(random.uniform(1, 2))
        elif self._check_basic_type(type_name, ["date"]):
            return time.strftime("%Y-%m-%d")
        elif self._check_basic_type(type_name, ["time"]):
            return time.strftime("%H:%M:%S")
        elif self._check_basic_type(type_name, ["dateTime"]):
            return time.strftime("%Y-%m-%d") + "T" + time.strftime("%H:%M:%S") + "Z"
        elif self._strip_prefix(type_name) in self._type_name_to_element:
            ret_val = "_" + type_name
            attribute_type_node = self._type_name_to_element[self._strip_prefix(type_name)]
            if attribute_type_node is not None:
                if attribute_type_node.tag == self._add_prefix(Constants.SIMPLE_TYPE):
                    (singleton_list, _) = self._parse_simple_type(attribute_type_node)
                    if len(singleton_list) > 0:
                        (_, this_type_value) = singleton_list[0]
                        ret_val = this_type_value
            return ret_val
        return "#" + type_name

    def _check_basic_type(self, variable, possible_list):
        for some_name in possible_list:
            if variable == "xs:" + some_name or variable == some_name:
                return True
        return False

    def _add_prefix(self, node_name):
        return self._namespace_prefix + node_name

    def _get_attribute_from_ref(self, ref_name):
        if ref_name == "xml:base":
            return ref_name, "xs:anyURI"
        elif ref_name == "xml:lang":
            return ref_name, "xs:language"
        else:
            return "", ""

    def _strip_prefix(self, attribute_name):
        return attribute_name[attribute_name.find(":") + 1:]

    def _is_int(self, s):
        """
        @s: string,
        @return, True if s can be successfully converted into string, else False
        """
        if s is None:
            return False
        try:
            int(s)
            return True
        except ValueError:
            return False


class XMLGenerator:
    _svg_parser = None
    _root_name = None
    _width = None
    _depth = None
    _xml_builder = None

    def __init__(self, path_svg, root_name, width, depth):
        self._svg_parser = SVGParser(path_svg)
        self._root_name = root_name
        self._width = width
        self._depth = depth
        self._xml_builder = ElementTree.TreeBuilder()

    def _get_xml_instance(self, element, depth):
        """
        @element: string, current element at which to continue generation
        @depth: int, Allowed depth of this element
        @return: None, everything needed is stored in _xml_builder
        """
        if depth < 0 or element is None or len(element) == 0:
            return
        elif depth == 0:
            max_children = 0
        else:
            max_children = self._width
        (children, attributes) = self._svg_parser.get_child_names(element, max_children)
        self._xml_builder.start(element, attributes)
        for (child_type, child_string) in children:
            if child_type == "data":
                self._xml_builder.data(child_string)
            else:
                self._get_xml_instance(child_string, depth - 1)
        self._xml_builder.end(element)

    def get_xml_instance(self):
        """
        @return: Element, root of xml instance generated
        """
        self._get_xml_instance(self._root_name, self._depth)
        root = self._xml_builder.close()
        some_namespace = self._svg_parser.get_target_namespace()
        if some_namespace is not None and len(some_namespace) > 0:
            root.set("xmlns", some_namespace)
        #start = self._xml_builder.start(self._root_name, {"xmlns": self._svg_parser.get_target_namespace()})
        #self._get_xml_instance(start, self._depth)
        #root = self._xml_builder.close()
        return root


def main():
    time_start = time.time()
    if len(sys.argv) < 6:
        print "Usage: xml_gen.py <path_svg.xsd> <root_name> <width> <depth> <timeout> <output_dir>"
        return
    path_svg = sys.argv[1]
    root_name = sys.argv[2]
    width = int(sys.argv[3])
    depth = int(sys.argv[4])
    timeout = int(sys.argv[5]) - 3
    output_dir = sys.argv[6]
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    xml_generator = XMLGenerator(path_svg, root_name, width, depth)
    base_name = os.path.splitext(os.path.basename(path_svg))[0]
    file_number = 0
    while (time.time() - time_start) < timeout:
        file_name = base_name + str(file_number) + ".xml"
        generated_file = open(os.path.join(output_dir, file_name), 'w')
        print "Start generating file " + file_name + "...",
        generated_root = xml_generator.get_xml_instance()
        element_tree = ElementTree.ElementTree(generated_root)
        element_tree.write(generated_file)
        print "Finish generating"
        file_number += 1
        generated_file.close()


if __name__ == "__main__":
    main()
    sys.exit(0)