# -*- coding: utf-8 -*-

# ********************************************************************
# This file contains copyrighted work from The Foundry,
# Sony Pictures Imageworks and Pixar, is intended for
# Katana and PRMan customers, and is not for distribution
# outside the terms of the corresponding EULA(s).
# ********************************************************************

# *******************
# !!2300줄 부터 수정!!
# *******************

from Katana import QtCore, QtGui, UI4, NodegraphAPI, DrawingModule, Nodes3DAPI

try:
    from Katana import QtWidgets
except ImportError:
    pass
from Katana import KatanaPrefs, GeoAPI
from Katana import Utils, Callbacks, Imath, logging
from Katana import RenderingAPI, FormMaster, FnGeolibServices, FnAttribute
from Katana import ScenegraphManager
import Katana
import os
import sys
import re
import math
import traceback
import platform


############################################################

from browser_modules import create_gaffer_modules
reload(create_gaffer_modules)

from browser_modules import create_image_package_run
reload(create_image_package_run)

from browser_modules import preview_widget_run
reload(preview_widget_run)

from browser_modules import browser_add_func
reload(browser_add_func)

from browser_modules import metadata_func
reload(metadata_func)

from browser_modules import cetegory_func
reload(cetegory_func)

############################################################

__qt_version__ = tuple([int(v) for v in QtCore.PYQT_VERSION_STR.split('.')])
if __qt_version__[0] == 4:
    QMessageBox = QtGui.QMessageBox
    QHBoxLayout = QtGui.QHBoxLayout
    QLabel = QtGui.QLabel
else:
    QMessageBox = QtWidgets.QMessageBox
    QHBoxLayout = QtWidgets.QHBoxLayout
    QLabel = QtWidgets.QLabel

_RMANVERSION_ = ''
_KATANAVERSION_ = '%d.%d' % (Katana.version[0], Katana.version[1])
_RMAN_FLOAT3_ = ['color', 'point', 'vector', 'normal']

# modules imported in _Initialized()
# declared here to make them global
ra = None
ral = None
rui = None
RmanAsset = None
FilePath = None
TrMode = None
TrStorage = None
TrSpace = None
TrType = None
ExternalFile = None
ColorManager = None

class RmanAssetKatanaError(Exception):
    """Exception class
    """

    def __init__(self, value):
        self.value = "RmanAssetKatana Error: %s" % value

        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(value)
        msgBox.setWindowTitle('Prman Preset Browser')
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def __str__(self):
        return repr(self.value)


def _set_python_paths(rmantree):
    rmanpath = os.path.join(rmantree, 'bin')
    if rmanpath not in sys.path:
        sys.path.append(rmanpath)

    rmanpath = os.path.join(rmantree, 'bin', 'pythonbindings')
    if rmanpath not in sys.path:
        sys.path.append(rmanpath)

    pyvers = 'python2.7'
    if float(_KATANAVERSION_) >= 5.0:
        pyvers = 'python3.7'

    site_pkgs = None
    if platform.system() == 'Windows':
        site_pkgs = os.path.join(rmantree, 'lib', pyvers, 'Lib', 'site-packages')
    else:
        site_pkgs = os.path.join(rmantree, 'lib', pyvers, 'site-packages')
    if site_pkgs not in sys.path:
        sys.path.append(site_pkgs)

# lazily load this only if the tab is instantiated
def _Initialize():
    global _RMANVERSION_
    if _RMANVERSION_:
        return

    if 'RMANTREE' in os.environ:
        rmantree = os.environ['RMANTREE']
        _set_python_paths(rmantree)

        try:
            global ra
            global ral
            global rui
            global RmanAsset
            global FilePath
            global TrMode
            global TrStorage
            global TrSpace
            global TrType
            global ExternalFile
            global ColorManager

            import rman_utils.rman_assets.core as ra
            import rman_utils.rman_assets.lib as ral
            import rman_utils.rman_assets.ui as rui
            from rman_utils.rman_assets.core import RmanAsset, FilePath
            from rman_utils.rman_assets.core import TrMode, TrStorage, TrSpace, TrType
            from rman_utils.rman_assets.common.external_files import ExternalFile
            from rman_utils.color_manager import ColorManager
            import rman
            prman_version = rman.Version
            grps = re.search(
                            '-([\d\.abrc]+)',
                            prman_version
                            )
            if len(grps.groups()) > 0:
                _RMANVERSION_ = grps.group(0)
                _RMANVERSION_ = _RMANVERSION_[1:]

            GetKatanaHostPrefsClass()

        except ImportError as err:
            tb = traceback.format_exc()
            logging.error(
                'Could not import necessary modules for the Preset Browser from RMANTREE (%s).' % rmantree)
            logging.error(
                '  |_ error message: %s).' % err)
            logging.error('traceback ----------\n%s', traceback.format_exc())

    else:
        logging.error('RMANTREE not set.')

def _sanitize_list(rman_type, val):
    """Return a native list type from input val, converting
    from Katana's vector type

    Arguments:
        rman_type {string} -- rman type
        val {} -- value to be sanitized

    Returns:
        rman_val {list} -- sanitized list

    """
    rman_val = val
    try:
        # Katana 3.1+ uses a ConstVector instead of list
        # attribute data.
        if isinstance(val, FnAttribute.ConstVector):
            rman_val = list()
            for i, v in enumerate(val):
                rman_val.append(v)
    except:
        pass

    return rman_val

def merge_nodes(nodes, parent):
    """Create a merge node between nodes and parent

    Arguments:
        nodes {list} -- list of nodes
        parent {Node} -- parent node to nodes

    """

    merge = NodegraphAPI.CreateNode("Merge", parent)

    nodes.sort(key=NodegraphAPI.GetNodePosition)
    for n in nodes:
        NodegraphAPI.SetNodeSelected(n, False)
        output = n.getOutputPortByIndex(0)
        if not output:
            continue
        numInputs = merge.getNumInputPorts()
        merge.addInputPort("i")
        input = merge.getInputPortByIndex(numInputs)
        output.connect(input)

    return merge


def _finished(
            node,
            nodeSelected=True, nodeEdited=True,
            nodeViewed=False):

    if nodeSelected is True:
        for n in NodegraphAPI.GetAllSelectedNodes():
            NodegraphAPI.SetNodeSelected(n, False)
        NodegraphAPI.SetNodeSelected(node, True)

    if nodeEdited is True:
        for n in NodegraphAPI.GetAllEditedNodes():
            NodegraphAPI.SetNodeEdited(n, False)
        NodegraphAPI.SetNodeEdited(node, True)

    if nodeViewed is True:
        NodegraphAPI.SetNodeViewed(node, True)

class RmanRamp:

    def __init__(self):
        self.values = []
        self.knots = []
        self.interp = ''
        self.is_color = False


def set_params(nodeName, node, paramsList):
    """Sets the params on a prman shading node

    Arguments:
        node {Node} -- prman shading node
        paramsList {list} -- param list from RmanAsset

    """

    node.checkDynamicParameters()
    nodeParams = node.getParameter('parameters')

    nodeType = node.getParameter('nodeType')

    policy = FormMaster.CreateParameterPolicy(None, nodeType)
    policy._thaw()
    policy.waitForReady()
    shaderType = policy.getValue()
    policy._freeze()

    del policy

    # ask for the RenderMan type via plug-in function
    shaderInfoAttr = FnGeolibServices.AttributeFunctionUtil.Run(
                    'PRManGetShaderInfo',
                    FnAttribute.StringAttribute(shaderType))

    if shaderInfoAttr is not None:
        shaderParams = shaderInfoAttr.getChildByName('params')

    ramps = dict()

    # Look for ramps
    for param in paramsList:
        pname = param.name()

        widget = shaderParams.getChildByName(pname + '.hints.widget')
        if widget:
            val = widget.getValue()
            if val in ['colorRamp', 'floatRamp']:
                rman_ramp = RmanRamp()
                ramps[pname] = rman_ramp

    for param in paramsList:
        ptype = param.type()
        pval = param.value()
        pname = param.name()

        if ptype is None or ptype == 'vstruct':
            continue
        if pval is None or pval == []:
            # connected param
            continue

        defaultAttr = shaderParams.getChildByName(pname + '.defaultAttr')
        if defaultAttr is not None:
            defaultVal = defaultAttr.getValue()
            if defaultAttr.getTupleSize() > 1:
                defaultVal = defaultAttr.getData()
            if defaultVal == pval:
                continue

        p = nodeParams.getChild(str(pname))
        if p is None:
            continue

        # check if we're dealing with a ramp param
        isRampParm = False
        for k in list(ramps):
            if k in pname:
                isRampParm = True
                rman_ramp = ramps[k]
                if 'Knots' in pname:
                    rman_ramp.knots = pval
                elif 'Colors' in pname:
                    rman_ramp.values = pval
                    rman_ramp.is_color = True
                elif 'Floats' in pname:
                    rman_ramp.values = pval
                elif 'Interpolation' in pname:
                    rman_ramp.interp = str(pval)

        if isRampParm:
            continue

        if 'string' in ptype:
            p.getChild('value').setValue(str(pval), 0)
            p.getChild('enable').setValue(1.0, 0)
        elif isinstance(pval, list):
            # rebuild array value parameters since dynamic arrays
            # may be a different size than the default
            val = p.getChild('value')
            if val:
                p.deleteChild(val)
            val = p.createChildNumberArray('value', len(pval))

            tokens = ptype.split('[')
            if tokens[0] in _RMAN_FLOAT3_:
                if isinstance(pval[0], list):
                    if val:
                        p.deleteChild(val)
                    val = p.createChildNumberArray('value', len(pval)*3)
                    # katana wants a flat list for colors
                    pval = [x for cols in pval for x in cols]

                val.setTupleSize(3)

            for i in range(len(pval)):
                try:
                    child = val.getChildByIndex(i)
                    if child:
                        child.setValue(pval[i], 0)
                except:
                    msg = ('set_params failed: %s.%s  ptype: \'%s\'  pval: %s'
                           % (nodeName, pname, ptype, repr(pval)))
                    logging.warning(msg)

            p.getChild('enable').setValue(1.0, 0)
        else:
            try:
                p.getChild('value').setValue(pval, 0)
                p.getChild('enable').setValue(1.0, 0)
            except:
                msg = ('set_params failed: %s.%s  ptype: \'%s\'  pval: %s'
                       % (nodeName, pname, ptype, repr(pval)))
                logging.warning(msg)

    # now, set ramp values on the node
    for k in list(ramps):
        ramp = ramps[k]

        knots = ramp.knots
        vals = ramp.values
        interp = ramp.interp
        if ramp.is_color:
            if isinstance(vals[0], list):
                # katana wants a flat list for colors
                vals = [x for col in vals for x in col]

        # double the first and last knot
        knots = knots[:1] + knots + knots[-1:]
        if ramp.is_color:
            vals = vals[:3] + vals + vals[-3:]
        else:
            vals = vals[:1] + vals + vals[-1:]

        p = nodeParams.getChild('%s' % str(k))
        if p:
            val = p.getChild('value')
            val.setValue(len(knots), 0)
            p.getChild('enable').setValue(1.0, 0)

        p = nodeParams.getChild('%s_Knots' % str(k))
        if p:
            val = p.getChild('value')
            p.deleteChild(val)
            val = p.createChildNumberArray('value', len(knots))
            for i in range(len(knots)):
                val.getChildByIndex(i).setValue(knots[i], 0)
            p.getChild('enable').setValue(1.0, 0)

        if ramp.is_color:
            p = nodeParams.getChild('%s_Colors' % str(k))
        else:
            p = nodeParams.getChild('%s_Floats' % str(k))

        if p:
            val = p.getChild('value')
            p.deleteChild(val)

            val = p.createChildNumberArray('value', len(vals))
            if ramp.is_color:
                val.setTupleSize(3)
            for i in range(len(vals)):
                val.getChildByIndex(i).setValue(vals[i], 0)
            p.getChild('enable').setValue(1.0, 0)

        p = nodeParams.getChild('%s_Interpolation' % str(k))
        if p:
            val = p.getChild('value')
            val.setValue(interp, 0)
            p.getChild('enable').setValue(1.0, 0)

def set_light_params(nodeName, node, paramsList):
    """Sets the light params on node

    Arguments:
        node {Node} -- light material
        paramsList {list} -- param list from RmanAsset

    """

    node.checkDynamicParameters()
    nodeParams = node.getParameters().getChild(
                                        'shaders').getChild(
                                                        'prmanLightParams')
    shaderType = node.getParameters().getChild('shaders').getChild(
                                                        'prmanLightShader')

    if nodeParams is None:
        nodeParams = node.getParameters().getChild('shaders').getChild(
                                                    'prmanLightfilterParams')
        shaderType = node.getParameters().getChild('shaders').getChild(
                                                    'prmanLightfilterShader')

    policy = FormMaster.CreateParameterPolicy(None, shaderType)
    policy._thaw()
    policy.waitForReady()
    shaderType = policy.getValue()
    policy._freeze()

    del policy

    # ask for the RenderMan type via plug-in function
    shaderInfoAttr = FnGeolibServices.AttributeFunctionUtil.Run(
                                            'PRManGetShaderInfo',
                                            FnAttribute.StringAttribute(
                                                        shaderType))

    shaderParams = shaderInfoAttr.getChildByName('params')

    ramps = dict()

    # Look for ramps
    for param in paramsList:
        pname = param.name()

        widget = shaderParams.getChildByName(pname + '.hints.widget')
        if widget:
            val = widget.getValue()
            if val in ['colorRamp', 'floatRamp']:
                rman_ramp = RmanRamp()
                ramps[pname] = rman_ramp

    for param in paramsList:
        ptype = param.type()
        pval = param.value()
        pname = param.name()

        if ptype is None or ptype == 'vstruct':
            continue
        if pval is None or pval == []:
            # connected param
            continue

        defaultAttr = shaderParams.getChildByName(pname + '.defaultAttr')
        if defaultAttr:
            defaultVal = defaultAttr.getValue()
            if defaultAttr.getTupleSize() > 1:
                defaultVal = defaultAttr.getData()
            if defaultVal == pval:
                continue

        p = nodeParams.getChild(str(pname))
        if p is None:
            continue

        # check if we're dealing with a ramp param
        isRampParm = False
        for k in list(ramps):
            if k in pname:
                isRampParm = True
                rman_ramp = ramps[k]
                if 'Knots' in pname:
                    rman_ramp.knots = pval
                elif 'Colors' in pname:
                    rman_ramp.values = pval
                    rman_ramp.is_color = True
                elif 'Floats' in pname:
                    rman_ramp.values = pval
                elif 'Interpolation' in pname:
                    rman_ramp.interp = str(pval)

        if isRampParm:
            continue

        if 'string' in ptype:
            p.getChild('value').setValue(str(pval), 0)
            p.getChild('enable').setValue(1.0, 0)
        elif isinstance(pval, list):
            # rebuild array value parameters since dynamic arrays
            # may be a different size than the default
            val = p.getChild('value')
            if val:
                p.deleteChild(val)
            val = p.createChildNumberArray('value', len(pval))

            tokens = ptype.split('[')
            if tokens[0] in _RMAN_FLOAT3_:
                val.setTupleSize(3)

            for i in range(len(pval)):
                child = val.getChildByIndex(i)
                if child:
                    child.setValue(pval[i], 0)

            p.getChild('enable').setValue(1.0, 0)
        else:
            try:
                p.getChild('value').setValue(pval, 0)
                p.getChild('enable').setValue(1.0, 0)
            except:
                msg = ('set_light_params failed: %s.%s  ptype: \'%s\'  pval: %s'
                       % (nodeName, pname, ptype, repr(pval)))
                logging.warning(msg)

    # now, set ramp values on the node
    for k in list(ramps):
        ramp = ramps[k]

        knots = ramp.knots
        vals = ramp.values
        interp = ramp.interp
        if ramp.is_color:
            if isinstance(vals[0], list):
                # katana wants a flat list for colors
                vals = [x for col in vals for x in col]

        # double the first and last knot
        knots = knots[:1] + knots + knots[-1:]
        if ramp.is_color:
            vals = vals[:3] + vals + vals[-3:]
        else:
            vals = vals[:1] + vals + vals[-1:]

        p = nodeParams.getChild('%s' % str(k))
        val = p.getChild('value')
        val.setValue(len(knots), 0)
        p.getChild('enable').setValue(1.0, 0)

        p = nodeParams.getChild('%s_Knots' % str(k))
        val = p.getChild('value')
        p.deleteChild(val)
        val = p.createChildNumberArray('value', len(knots))
        for i in range(len(knots)):
            val.getChildByIndex(i).setValue(knots[i], 0)
        p.getChild('enable').setValue(1.0, 0)

        if ramp.is_color:
            p = nodeParams.getChild('%s_Colors' % str(k))
        else:
            p = nodeParams.getChild('%s_Floats' % str(k))

        val = p.getChild('value')
        p.deleteChild(val)
        val = p.createChildNumberArray('value', len(vals))
        if ramp.is_color:
            val.setTupleSize(3)
        for i in range(len(vals)):
            val.getChildByIndex(i).setValue(vals[i], 0)
        p.getChild('enable').setValue(1.0, 0)

        p = nodeParams.getChild('%s_Interpolation' % str(k))
        val = p.getChild('value')
        val.setValue(interp, 0)
        p.getChild('enable').setValue(1.0, 0)


def connect_nodes(Asset, nodeDict, nodeList, rootNode):
    """ Wire the connections for the material network using the connection
    list from Asset.

    Arguments:
        Asset {RmanAsset} -- the asset which has the info about the material network
        nodeDict {dict} -- dictionary of nodeIDs to Katana nodes. This should be
                                 the dictionary returned by create_nodes
        nodeList {list} -- list of nodes in this network. Will be used to do autoposition
        rootNode (str, NodegraphAPI.Node) -- a pair with the first element being the name of
                        the root shadingEngine node if it exists, and the second element being
                        the network material node for this material.

    """

    # map of all parameter connections into an array parameter
    # format - {dstNode.dstParam : [(srcNode.srcParam, arrayIndex), (.., ..), ...]}
    arrayConnections = {}

    # list of all terminal nodes (nodes without outgoing connections)
    unconnectedNodes = []
    for n in nodeList:
        unconnectedNodes.append(n)

    rootName = rootNode[0]
    networkMtlNode = rootNode[1]

    for con in Asset.connectionList():
        rootConnection = (con.dstNode() == rootName)

        if (con.srcNode() not in nodeDict) or ((not rootConnection) and (con.dstNode() not in nodeDict)):
            continue

        if (rootConnection):
            dstNode = networkMtlNode
        else:
            dstNode = nodeDict[con.dstNode()]
        srcNode = nodeDict[con.srcNode()]
        srcAttr = con.srcParam()
        dstAttr = con.dstParam()

        # node has connection, remove it from unconnected list
        if srcNode in unconnectedNodes:
            unconnectedNodes.remove(srcNode)

        # save connections to array parameters to handle outside of loop
        if '[' in dstAttr:
            dstNodeParam = con.dstNodeParam().split("[")[0]
            inputIndex = con.dstNodeParam().split("[")[1].split(']')[0]
            if dstNodeParam in list(arrayConnections):
                arrayConnections[dstNodeParam].append((con.srcNodeParam(), int(inputIndex)))
            else:
                arrayConnections[dstNodeParam] = [(con.srcNodeParam(), int(inputIndex))]
            continue

        srcPort = srcNode.getOutputPort(str(srcAttr))
        dstPort = dstNode.getInputPort(str(dstAttr))

        # ask for the RenderMan type via plug-in function
        nodeType = srcNode.getParameter('nodeType').getValue(0)
        shaderInfoAttr = FnGeolibServices.AttributeFunctionUtil.Run(
                                                    'PRManGetShaderInfo',
                                                    FnAttribute
                                                    .StringAttribute(
                                                    nodeType)
                                                    )
        shaderType = shaderInfoAttr.getChildByName('shaderTypeTags').getValue('')
        # the different DCCs use different names for the outputs of non-pattern nodes
        # instead, assume the first output port is the one we want to connect
        if shaderType != 'pattern':
            srcPort = srcNode.getOutputPortByIndex(0)

        # use the correct ports on the network material node for connections to the root node
        if rootConnection:
            if dstAttr == 'rman__surface':
                dstPort = networkMtlNode.getInputPort('prmanBxdf')
            elif dstAttr == 'rman__displacement':
                dstPort = networkMtlNode.getInputPort('prmanDisplacement')
            else:
                # this is an unsupported connection type
                continue

        if srcPort.isConnected(dstPort) is False:
            srcPort.connect(dstPort)

    # handle connections to array parameters
    for dst in list(arrayConnections):
        dstNode = nodeDict[dst.split('.')[0]]
        dstPort = dstNode.getInputPort(dst.split('.')[1])

        # create a SNAC node for these array param cconnections
        parentGroup = dstNode.getParent()
        SNAC = NodegraphAPI.CreateNode('ShadingNodeArrayConnector', parentGroup)
        SNAC.setName('SNAC_' + dst.replace('.', '_'))
        nodeList.append(SNAC)

        # connect SNAC output to dstPort
        outPort = SNAC.getOutputPort('out')
        if outPort.isConnected(dstPort) is False:
            outPort.connect(dstPort)

        srcList = arrayConnections[dst]
        orderedSrcList = [x[0] for x in sorted(srcList, key=lambda tup: tup[1])]
        idx = 0
        for src in orderedSrcList:
            srcNode = nodeDict[src.split('.')[0]]
            srcPort = srcNode.getOutputPort(src.split('.')[1])

            # connect the src port to a new input port in the SNAC node
            SNAC.addInputPortAtIndex('i'+str(idx), idx)
            inPort = SNAC.getInputPort('i'+str(idx))
            if srcPort.isConnected(inPort) is False:
                srcPort.connect(inPort)
            idx += 1

    # connect terminal nodes to the NetworkMaterial node
    for node in unconnectedNodes:
        # ask for the RenderMan type via plug-in function
        nodeType = node.getParameter('nodeType').getValue(0)
        shaderInfoAttr = FnGeolibServices.AttributeFunctionUtil.Run(
                                                    'PRManGetShaderInfo',
                                                    FnAttribute
                                                    .StringAttribute(
                                                    nodeType)
                                                    )
        shaderType = shaderInfoAttr.getChildByName('shaderTypeTags').getValue('')
        if shaderType == 'pattern':
            continue

        dstPortName = 'prman' + shaderType.capitalize()
        dstPort = networkMtlNode.getInputPort(dstPortName)
        if not dstPort:
            dstPort = networkMtlNode.addInputPort(dstPortName)

        # only connect this node to the network material if it has no other connections
        # it's possible that this unconnected node is just a rogue node rather than a
        # terminal node.  If there was a root node in the preset, it's connections would
        # be made above and should take precedence.
        if dstPort.getNumConnectedPorts() == 0:
            node.getOutputPortByIndex(0).connect(dstPort)


    if len(nodeList) > 0:
        DrawingModule.AutoPositionNodes(nodeList)


def set_node_name_param(node, name):

    """Set node's name parameter to match node's unique name

    Arguments:
        node {Node} -- node to be renamed
        name {String} -- requested new name

    Returns:
        uniqueName {String} -- node's new, unique name

    """

    '''
    Guarantee that the node name parameter matches the node name as multiple copies of
    an asset are imported. When a node is renamed with an existing node name (e.g.
    "Silver_NetworkMaterial") the node name gets a unique suffix, however the node's
    name parameter does not automatically take on that unique name. Notes from stevel:
    The node param value drives node name via the event 'parameter_finalizeValue'
    The code which manages this synchronization, for registered node types, listens to parameter
    change events on those nodes and does the name sync in response to that.
    In the UI, events are processed right away.
    In script, events are not processed automatically.
    So, we set the param, push the event through, get the new (unique) name and set the param again.
    '''

    node.getParameter('name').setValue(name, 0)
    Utils.EventModule.ProcessAllEvents()

    uniqueName = node.getName()
    node.getParameter('name').setValue(uniqueName, 0)
    Utils.EventModule.ProcessAllEvents()

    return uniqueName

def create_materialGroup(Asset, assignToSelected, assignToRoot=False):
    """Create the node structure of an imported material:
            the containing Group, NetworkMaterial, and MaterialAssign

    Arguments:
        Asset {RmanAsset} -- the asset which has the info about the material network

    Returns:
        shadingNetworkGroupNode {NodegraphAPI.Node}  -- the group node that will
                                                        contain the PrmanShadingNodes
        networkMtlNode {NodegraphAPI.Node} -- the NetworkMaterial node for this material

    """

    # Get the root node
    ngt = UI4.App.Tabs.FindTopTab('Node Graph')
    if ngt is not None:
        root = ngt.getEnteredGroupNode()
    else:
        root = NodegraphAPI.GetRootNode()

    # Use viewport position as basis for positioning new nodes
    pos = NodegraphAPI.GetViewPortPosition(root)
    posX = pos[0][0]
    posY = pos[0][1]

    # Name of asset
    label = Asset.label()
    label = re.sub(r'[\s:]+', '_', label)

    # Create Group to contain all nodes for this asset
    assetGroupNode = NodegraphAPI.CreateNode('Group', root)
    assetGroupNode.setName(str(label))

    # Create Group to contain the PrmanShadingNode network
    shadingNetworkGroupNode = NodegraphAPI.CreateNode('Group', assetGroupNode)
    shadingNetworkGroupNode.setName(str(label) + '_ShadingNetworkGroup')

    # Create NetworkMaterial for the shading network
    networkMtlNode = NodegraphAPI.CreateNode('NetworkMaterial', assetGroupNode)
    set_node_name_param(networkMtlNode, str(label)+'_NetworkMaterial')


    # Set up dot as input to merge with NetworkMaterial
    inDotNode = NodegraphAPI.CreateNode('Dot', assetGroupNode)
    inDotNode.setName(str(label) + '_InPort')

    # Merge incoming connection with shading network
    mergeNode = merge_nodes([inDotNode, networkMtlNode], assetGroupNode)
    mergeOutput = mergeNode.getOutputPortByIndex(0)

    # Add an input port to the overall group, then wire its "send" port to the
    # input Dot node which allows a node outside of the group to be wired into our input.
    assetGroupInput    = assetGroupNode.addInputPort("in")
    assetGroupSendPort = assetGroupNode.getSendPort("in")
    inDotInput        = inDotNode.getInputPortByIndex(0)
    inDotInput.connect(assetGroupSendPort)


    # Add an output port to overall group then get its "return" port
    # which allows for connecting to a downstream node.
    assetGroupOutPort = assetGroupNode.addOutputPort("out")
    assetGroupReturnPort = assetGroupNode.getReturnPort("out")

    # Build MaterialAssign node
    materialAssignNode = NodegraphAPI.CreateNode('MaterialAssign', assetGroupNode)
    materialAssignNode.setName(str(label) + '_MaterialAssign')

    # Fill out the material assign param with our new material
    materialAssignNode.getParameter('args.materialAssign.value').setExpression(
                'scenegraphLocationFromNode(getNode(%r))' % networkMtlNode.getName())
    materialAssignNode.getParameter('args.materialAssign.enable').setValue(1, 0)



    # DrawingModule.AutoPositionNodes([...])
    # falls apart with more than a few nodes so we'll do it manually
    NodegraphAPI.SetNodePosition(assetGroupNode,          (posX,     posY))
    NodegraphAPI.SetNodePosition(inDotNode,               (posX-260, posY+120))
    NodegraphAPI.SetNodePosition(shadingNetworkGroupNode, (posX,     posY+100))
    NodegraphAPI.SetNodePosition(networkMtlNode,          (posX,     posY))
    NodegraphAPI.SetNodePosition(mergeNode,               (posX-250, posY-100))
    NodegraphAPI.SetNodePosition(materialAssignNode,      (posX-250, posY-200))

    # Connect Merge --> MaterialAssign
    materialAssignInput = materialAssignNode.getInputPortByIndex(0)
    mergeOutput.connect(materialAssignInput)

    # Connect MaterialAssign --> group return
    materialAssignOutput = materialAssignNode.getOutputPortByIndex(0)
    materialAssignOutput.connect(assetGroupReturnPort)

    # Expose the MaterialAssign.CEL parameter on the parent group
    assignmentCelP = assetGroupNode.getParameters().createChildString('assignmentCEL', '')
    assignmentCelP.setHintString(repr({'widget' : 'cel',}))
    materialAssignNode.getParameter('CEL').setExpression('=^/assignmentCEL')

    # See if we can or should assign this material to selected scenegraph locations
    locs = []
    if assignToRoot:
        locs.append('/root')
    elif assignToSelected:
        locs = ScenegraphManager.getActiveScenegraph().getSelectedLocations()
    if len(locs) > 0:
        # Space-delimted single string list of selected scene-graph locations
        cel = ' '.join(locs)
        assignmentCelP.setValue(cel,0)


    _finished(assetGroupNode,
            nodeSelected=True,
            nodeEdited=True,
            nodeViewed=False)

    # Switch on floating "placement mode" for main group node
    nodeGraphTab = UI4.App.Tabs.FindTopTab('Node Graph')
    nodeGraphTab.prepareFloatingLayerWithPasteBounds([assetGroupNode])
    nodeGraphTab.enableFloatingLayer()

    return networkMtlNode, shadingNetworkGroupNode

def create_displayFilters(Asset, assignToSelected):
    """Create display filter nodes from asset. The current assumption is that if an asset contains
        items in the displayFilterList, it is a display filter asset rather than a material.

    Arguments:
        Asset {RmanAsset} -- the asset which has the info about the material network
    """
    networkMtlNode, shadingNetworkGroupNode = create_materialGroup(Asset, assignToSelected, True)

    # Build shading network
    nodeList = []
    rootName = ''
    for df in Asset.displayFilterList():
        nodeId = df.name()
        rmanNode = df.rmanNode()
        nodeLabel = re.sub(r'[\s:]+', '_', nodeId)

        # print 'create_nodes: %s %s: %s' % (nodeId, nodeType, nodeClass)
        # fmt, vals, ttype = node.transforms()
        # print '| %s %s: %s' % (fmt, vals, ttype)

        transformName = None
        dfNode = NodegraphAPI.CreateNode('PrmanShadingNode', shadingNetworkGroupNode)
        set_node_name_param(dfNode, str(nodeLabel))
        dfNode.getParameter('nodeType').setValue(str(rmanNode), 0)

        nodeList.append(dfNode)

        set_params(nodeLabel, dfNode, df.paramsDict())

    # create a combiner + SNAC node in case there are multiple display filters
    combinerNode = NodegraphAPI.CreateNode('PrmanShadingNode', shadingNetworkGroupNode)
    set_node_name_param(combinerNode, str('PxrDisplayFilterCombiner'))
    combinerNode.getParameter('nodeType').setValue('PxrDisplayFilterCombiner', 0)
    combinerNode.checkDynamicParameters()
    SNAC = NodegraphAPI.CreateNode('ShadingNodeArrayConnector', shadingNetworkGroupNode)
    SNAC.setName('SNAC_displayFilters')

    # connect SNAC output to dstPort
    outPort = SNAC.getOutputPort('out')
    dstPort = combinerNode.getInputPort('filter')
    outPort.connect(dstPort)

    # connect display filters to SNAC
    idx = 0
    for node in nodeList:
        outPort = node.getOutputPort('out')
        SNAC.addInputPortAtIndex('i'+str(idx), idx)
        dstPort = SNAC.getInputPort('i'+str(idx))
        if outPort.isConnected(dstPort) is False:
            outPort.connect(dstPort)
        idx += 1

    # connect combiner to NetworkMaterial port
    dstPort = networkMtlNode.addInputPort('prmanDisplayfilter')
    outPort = combinerNode.getOutputPort('out')
    outPort.connect(dstPort)

    # makee it pretty
    if len(nodeList) > 0:
        nodeList.append(combinerNode)
        nodeList.append(SNAC)
        DrawingModule.AutoPositionNodes(nodeList)

    return

def create_nodes(Asset, assignToSelected):
    """Create nodes necessary for a material network from Asset

    Arguments:
        Asset {RmanAsset} -- the asset which has the info about the material network

    Returns:
        nodesDict {dict} -- a dictionary of nodeIDs to Katana nodes
        nodeList {list}  -- list of all the nodes for this material network
        rootNode (pair(str, Node)) -- pair containing the NetworkMaterial node and
                                      the nodeid representing it in the asset

    """
    networkMtlNode, shadingNetworkGroupNode = create_materialGroup(Asset, assignToSelected)

    # Build shading nodes
    nodeList = []
    nodeDict = {}
    rootName = ''
    for node in Asset.nodeList():
        nodeId = node.name()
        nodeType = node.type()
        nodeClass = node.nodeClass()
        rmanNode = node.rmanNode()

        # print 'create_nodes: %s %s: %s' % (nodeId, nodeType, nodeClass)
        # fmt, vals, ttype = node.transforms()
        # print '| %s %s: %s' % (fmt, vals, ttype)

        nodeLabel = re.sub(r'[\s:]+', '_', nodeId)
        transformName = None

        if nodeType == 'coordinateSystem':
            # print 'not supported'
            continue
        elif nodeType == 'shadingEngine':
            if nodeClass == 'root':
                validRootNode = False
                for param in node.paramsDict():
                    if param.name() == 'rman__surface' and param.value() is None:
                        networkMtlNode.addInputPort('prmanBxdf')
                        validRootNode = True
                    if param.name() == 'rman__displacement' and param.value() is None:
                        networkMtlNode.addInputPort('prmanDisplacement')
                        validRootNode = True
                if validRootNode:
                    rootName = nodeId
            continue
        elif nodeClass == 'bxdf':
            # print '| case: bxdf: %s' % (nodeId)

            bxdfNode = NodegraphAPI.CreateNode('PrmanShadingNode', shadingNetworkGroupNode)
            set_node_name_param(bxdfNode, str(nodeLabel))
            bxdfNode.getParameter('nodeType').setValue(str(rmanNode), 0)

            nodeList.append(bxdfNode)

            set_params(nodeLabel, bxdfNode, node.paramsDict())

            nodeDict[nodeId] = bxdfNode

        elif nodeClass == 'displace':
            # print '| case: displace: %s' % (nodeId)

            dispNode = NodegraphAPI.CreateNode('PrmanShadingNode', shadingNetworkGroupNode)
            set_node_name_param(dispNode, str(nodeLabel))
            dispNode.getParameter('nodeType').setValue(str(rmanNode), 0)

            nodeList.append(dispNode)

            set_params(nodeLabel, dispNode, node.paramsDict())

            nodeDict[nodeId] = dispNode

        elif nodeClass == 'pattern':

            patternNode = NodegraphAPI.CreateNode('PrmanShadingNode', shadingNetworkGroupNode)
            set_node_name_param(patternNode, str(nodeLabel))

            if node.externalOSL() is False:
                patternNode.getParameter('nodeType').setValue(str(rmanNode), 0)
            else:
                if not nodeType.endswith('.oso'):
                    pathToOSL = Asset.getDependencyPath(ExternalFile.k_osl, nodeType + '.oso')
                else:
                    pathToOSL = Asset.getDependencyPath(ExternalFile.k_osl, nodeType)
                if pathToOSL is None:
                    err = ('create_nodes: OSL file is missing "%s"'
                           % nodeType)
                    raise RmanAssetKatanaError(err)

                patternNode.getParameter('nodeType').setValue(str(pathToOSL), 0)

            nodeList.append(patternNode)
            set_params(nodeLabel, patternNode, node.paramsDict())
            nodeDict[nodeId] = patternNode

    return (nodeDict, nodeList, (rootName, networkMtlNode))



def import_light_rig(Asset):
    """Imprt a light rig from Asset creating a new GafferThree node

    Arguments:
        Asset {RmanAsset} -- the asset tha has the info about the light rig.
    """
    ngt = UI4.App.Tabs.FindTopTab('Node Graph')
    if ngt is not None:
        root = ngt.getEnteredGroupNode()
    else:
        root = NodegraphAPI.GetRootNode()

    pos = NodegraphAPI.GetViewPortPosition(root)
    gaffer = NodegraphAPI.CreateNode('GafferThree', root)
    gaffer.setName(str(Asset.label()) + '_GafferThree')
    NodegraphAPI.SetNodePosition(gaffer, (pos[0][0], pos[0][1]))

    _finished(
            gaffer,
            nodeSelected=True, nodeEdited=True,
            nodeViewed=False)
    lights = {}
    lightfilters = {}
    lightfilterpkgnames = {}

    for node in Asset.nodeList():
        nodeId = node.name()
        nodeType = node.type()
        nodeClass = node.nodeClass()
        nodeLabel = re.sub(r'[\s:]+', '_', nodeId)

        # FIXME
        # For now, skip if we encounter a mesh light.
        # RfK requires a geometry be selected to create a PxrMeshLight.
        # However, the preset asset JSON file doesn't specify what geometry
        # the mesh light was connected to.
        if nodeType == 'PxrMeshLight':
            continue

        fmt, vals, ttype = node.transforms()

        rootPackage = gaffer.getRootPackage()
        light = None
        lightMaterial = None
        if nodeClass == 'light':
            light = rootPackage.createChildPackage(nodeType + 'Package')
            lights[nodeId] = light.getLocationPath()
            lightMaterial = light.getMaterialNode()
        elif nodeClass == 'lightfilter':
            light = rootPackage.createChildPackage(nodeType + 'Package')
            lightfilters[nodeId] = light.getLocationPath()
            lightfilterpkgnames[nodeId] = light.getPackageNode().getName()
            lightMaterial = light.getMaterialNode()

        else:
            continue

        set_light_params(nodeLabel, lightMaterial, node.paramsDict())
        lightcreate = light.getCreateNode()

        if fmt[2] == TrMode.k_flat:
            if fmt[0] == TrStorage.k_TRS:
                interface = lightcreate.getParameter('transform.interface')
                interface.setValue('SRT Values', 0)

                xt = lightcreate.getParameter('transform.translate.x')
                yt = lightcreate.getParameter('transform.translate.y')
                zt = lightcreate.getParameter('transform.translate.z')

                xt.setValue(vals[0], 0)
                yt.setValue(vals[1], 0)
                zt.setValue(vals[2], 0)

                xr = lightcreate.getParameter('transform.rotate.x')
                yr = lightcreate.getParameter('transform.rotate.y')
                zr = lightcreate.getParameter('transform.rotate.z')

                xr.setValue(vals[3], 0)
                yr.setValue(vals[4], 0)
                zr.setValue(vals[5], 0)

                xs = lightcreate.getParameter('transform.scale.x')
                ys = lightcreate.getParameter('transform.scale.y')
                zs = lightcreate.getParameter('transform.scale.z')

                xs.setValue(vals[6], 0)
                ys.setValue(vals[7], 0)
                zs.setValue(vals[8], 0)

            elif fmt[0] == TrStorage.k_matrix:

                mtx = Imath.M44f(vals)
                scale = Imath.V3d()
                shear = Imath.V3d()
                rotate = Imath.V3d()
                translate = Imath.V3d()
                scale, shear, rotate, translate = mtx.extractSHRT()

                interface = lightcreate.getParameter('transform.interface')
                interface.setValue('SRT Values', 0)

                xt = lightcreate.getParameter('transform.translate.x')
                yt = lightcreate.getParameter('transform.translate.y')
                zt = lightcreate.getParameter('transform.translate.z')

                xt.setValue(translate[0], 0)
                yt.setValue(translate[1], 0)
                zt.setValue(translate[2], 0)

                xr = lightcreate.getParameter('transform.rotate.x')
                yr = lightcreate.getParameter('transform.rotate.y')
                zr = lightcreate.getParameter('transform.rotate.z')

                xr.setValue(math.degrees(rotate[0]), 0)
                yr.setValue(math.degrees(rotate[1]), 0)
                zr.setValue(math.degrees(rotate[2]), 0)

                xs = lightcreate.getParameter('transform.scale.x')
                ys = lightcreate.getParameter('transform.scale.y')
                zs = lightcreate.getParameter('transform.scale.z')

                xs.setValue(scale[0], 0)
                ys.setValue(scale[1], 0)
                zs.setValue(scale[2], 0)

            else:
                raise RmanAssetKatanaError('Unsupported transform mode !\
                (hierarchical)')
        else:
            raise RmanAssetKatanaError('Unsupported transform mode !\
            (hierarchical)')

    for con in Asset.connectionList():

        srcNode = con.srcNode()
        dstNode = con.dstNode()

        light = None
        lightfilterloc = None
        lightfilterpkgname = None

        if srcNode in list(lightfilters):
            lightfilterloc = lightfilters[srcNode]
            lightfilterpkgname = lightfilterpkgnames[srcNode]
        elif srcNode in list(lights):
            loc = lights[srcNode]
            light = gaffer.getPackageForPath(loc)

        if dstNode in list(lightfilters):
            lightfilterloc = lightfilters[dstNode]
            lightfilterpkgname = lightfilterpkgnames[dstNode]
        elif dstNode in list(lights):
            loc = lights[dstNode]
            light = gaffer.getPackageForPath(loc)

        if light and lightfilterloc and lightfilterpkgname:
            lightfilterrefpkg = light.createChildPackage(
                                    'LightFilterReferencePackage')
            lightfilterref = lightfilterrefpkg.getInternalNode()
            lfrefexpr = '=' + lightfilterpkgname + '/__gaffer.location'
            lightfilterref.getParameter('args.referencePath.value').setExpression(
                                                        lfrefexpr, True)
            lightfilterref.getParameter('args.referencePath.enable').setValue(
                                                        1, 0)


def import_envmap(Asset, lightName=None):
    """Import an envmap from Asset into a new GafferThree node

    Arguments:
        Asset {RmanAsset} -- the asset that has the infos about the env map preset
        lightName {str} -- name of light

    """

    envMapPath = Asset.envMapPath()

    try:
        ngt = UI4.App.Tabs.FindTopTab('Node Graph')
        if ngt is not None:
            root = ngt.getEnteredGroupNode()
        else:
            root = NodegraphAPI.GetRootNode()
        pos = NodegraphAPI.GetViewPortPosition(root)
        label = str(Asset.label())
        label = re.sub(r'\s+', '_', label)

        gaffer = NodegraphAPI.CreateNode('GafferThree', root)
        gaffer.setName(label + '_GafferThree')
        NodegraphAPI.SetNodePosition(gaffer, (pos[0][0], pos[0][1]))

        _finished(
                gaffer,
                nodeSelected=True,
                nodeEdited=True,
                nodeViewed=False)
        rootPackage = gaffer.getRootPackage()
        light = rootPackage.createChildPackage('PxrDomeLightPackage')
        mat = light.getMaterialNode()
        mat.checkDynamicParameters()
        params = mat.getParameters().getChild('shaders').getChild(
                                                    'prmanLightParams')
        shader = mat.getParameters().getChild('shaders').getChild(
                                                    'prmanLightShader')
        p = params.getChild('lightColorMap')
        p.getChild('enable').setValue(1.0, 0)
        p.getChild('value').setValue(str(envMapPath), 0)

    except Exception as e:
        raise RmanAssetKatanaError('Could not import env map: ' + str(e))


def parse_node_graph(nodes, Asset, isLightRig=False):
    """Parses the graph for each node in nodes

    Arguments:
        nodes {list} -- list of nodes to export
        Asset {RmanAsset} -- the asset in which the infos will be stored.
        isLightRig {bool} -- True if we're exporting a light rig. False otherwise.
    """

    viewNode = NodegraphAPI.GetViewNode()
    producer = Nodes3DAPI.GetGeometryProducer(node=viewNode)

    if isLightRig is True:

        lightfilters = []

        for n in nodes:

            lightpkg = None
            numOfLightFilters = 0

            try:
                light = producer.getProducerByPath(n)
                mat = light.getAttribute('material')
                params = mat.getChildByName('prmanLightParams')
                shader = mat.getChildByName('prmanLightShader')
            except:
                continue
            xform = light.getAttribute('xform').getChildByName('interactive')
            shaderName = shader.getValue('')
            nodeName = os.path.basename(n)

            # ask for the RenderMan type via plug-in function
            shaderInfoAttr = FnGeolibServices.AttributeFunctionUtil.Run(
                                                    'PRManGetShaderInfo',
                                                    FnAttribute
                                                    .StringAttribute(
                                                                shaderName)
                                                    )

            Asset.addNode(nodeName, shaderName, 'light', shaderName)

            xformVals = []
            translate = xform.getChildByName('translate')
            rotateX = xform.getChildByName('rotateX')
            rotateY = xform.getChildByName('rotateY')
            rotateZ = xform.getChildByName('rotateZ')
            scale = xform.getChildByName('scale')

            xformVals.append(translate.getData()[0])
            xformVals.append(translate.getData()[1])
            xformVals.append(translate.getData()[2])
            xformVals.append(rotateX.getData()[0])
            xformVals.append(rotateY.getData()[0])
            xformVals.append(rotateZ.getData()[0])
            xformVals.append(scale.getData()[0])
            xformVals.append(scale.getData()[1])
            xformVals.append(scale.getData()[2])

            Asset.addNodeTransform(nodeName, xformVals, TrStorage.k_TRS)

            if params:
                for name, p in params.childList():
                    try:

                        shaderParams = shaderInfoAttr.getChildByName('params')
                        typeVal = shaderParams.getChildByName(name).getChildByName(
                                                                'type').getValue()
                        defaultAttr = shaderParams.getChildByName(
                                                            name).getChildByName(
                                                                'defaultAttr')
                    except:
                        continue

                    rman_type = 'float'
                    if typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypePoint3):
                        rman_type = 'point'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeColor3):
                        rman_type = 'color'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeVector3):
                        rman_type = 'vector'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeNormal):
                        rman_type = 'normal'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeMatrix):
                        rman_type = 'matrix'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeString):
                        rman_type = 'string'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeInt):
                        rman_type = 'int'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypePointer):
                        rman_type = 'struct'

                    value = p.getValue()
                    defaultVal = defaultAttr.getValue()

                    if (p.getNumberOfValues() > 1):
                        value = p.getData()
                        defaultVal = defaultAttr.getData()

                    rman_val = _sanitize_list(rman_type, value)
                    rman_default_val = _sanitize_list(rman_type, defaultVal)

                    Asset.addParam(
                        nodeName, shaderName, name,
                        {'type': rman_type, 'value': rman_val, 'default': rman_default_val})

            path = n
            for child in light.iterChildren():
                child_path = path + '/' + child.getName()
                if child.getType() == 'light filter':
                    lightfilters.append(child_path)
                    lightfilter = producer.getProducerByPath(child_path)
                    mat = lightfilter.getAttribute('material')
                    if mat:
                        dst = '%s.rman__lightfilters[%d]' % (nodeName,
                                                             numOfLightFilters)
                        src = '%s.message' % (str(child.getName()))
                        Asset.addConnection(src, dst)
                        numOfLightFilters += 1
                        if child_path not in lightfilters:
                            lightfilters.append(child_path)
                elif child.getType() == 'light filter reference':
                    world = producer.getProducerByPath('/root/world')
                    lightList = world.getAttribute('lightList')

                    for lightName, l in lightList.childList():
                        if l.getChildByName('path').getValue('') == child_path:
                            referencePath = l.getChildByName(
                                                'referencePath').getValue('')
                            lightfilter = producer.getProducerByPath(
                                                        referencePath)
                            mat = lightfilter.getAttribute('material')
                            if mat:
                                dst = '%s.rman__lightfilters[%d]' % (
                                                nodeName,
                                                numOfLightFilters)
                                src = '%s.message' % (str(referencePath.split('/')[-1]))
                                Asset.addConnection(src, dst)
                                numOfLightFilters += 1
                                if referencePath not in lightfilters:
                                    lightfilters.append(referencePath)

                    continue

        for lf in lightfilters:

            nodeName = os.path.basename(lf)
            params = None
            shader = None
            try:
                lightfilter = producer.getProducerByPath(lf)
                mat = lightfilter.getAttribute('material')
                params = mat.getChildByName('prmanLightfilterParams')
                shader = mat.getChildByName('prmanLightfilterShader')
            except:
                continue
            if shader is None:
                continue

            xform = lightfilter.getAttribute('xform').getChildByName('interactive')
            shaderName = shader.getValue('')
            shaderType = shaderName
            # ask for the RenderMan type via plug-in function
            shaderInfoAttr = FnGeolibServices.AttributeFunctionUtil.Run(
                            'PRManGetShaderInfo',
                            FnAttribute.StringAttribute(shaderType))

            Asset.addNode(nodeName, shaderName, 'lightfilter', shaderName)

            xformVals = []
            translate = xform.getChildByName('translate')
            rotateX = xform.getChildByName('rotateX')
            rotateY = xform.getChildByName('rotateY')
            rotateZ = xform.getChildByName('rotateZ')
            scale = xform.getChildByName('scale')

            xformVals.append(translate.getData()[0])
            xformVals.append(translate.getData()[1])
            xformVals.append(translate.getData()[2])
            xformVals.append(rotateX.getData()[0])
            xformVals.append(rotateY.getData()[0])
            xformVals.append(rotateZ.getData()[0])
            xformVals.append(scale.getData()[0])
            xformVals.append(scale.getData()[1])
            xformVals.append(scale.getData()[2])

            Asset.addNodeTransform(nodeName, xformVals, TrStorage.k_TRS)

            if params is None:
                continue

            for name,p in params.childList():
                try:

                    shaderParams = shaderInfoAttr.getChildByName('params')
                    typeVal = shaderParams.getChildByName(name).getChildByName(
                                'type').getValue()
                    defaultAttr = shaderParams.getChildByName(
                                                name).getChildByName(
                                                'defaultAttr')
                except:
                    continue

                rman_type = 'float'
                if typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypePoint3):
                    rman_type = 'point'
                elif typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypeColor3):
                    rman_type = 'color'
                elif typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypeVector3):
                    rman_type = 'vector'
                elif typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypeNormal):
                    rman_type = 'normal'
                elif typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypeMatrix):
                    rman_type = 'matrix'
                elif typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypeString):
                    rman_type = 'string'
                elif typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypeInt):
                    rman_type = 'int'
                elif typeVal == (
                                RenderingAPI.RendererInfo.
                                kRendererObjectValueTypePointer):
                    rman_type = 'struct'

                value = p.getValue()
                defaultVal = defaultAttr.getValue()

                if (p.getNumberOfValues() > 1):
                    value = p.getData()
                    defaultVal = defaultAttr.getData()

                rman_val = _sanitize_list(rman_type, value)
                rman_default_val = _sanitize_list(rman_type, defaultVal)
                Asset.addParam(
                    nodeName, shaderName, name,
                    {'type': rman_type, 'value': rman_val, 'default': rman_default_val})

    else:

        for n in list(nodes):

            prod = producer.getProducerByPath(n)
            mat = prod.getGlobalAttribute('material')
            nodes = mat.getChildByName('nodes')
            bxdf = ''
            displacement = ''
            displayfilter = ''

            exportDisplayFilters = False

            try:
                terms = mat.getChildByName('terminals')
                if terms.getChildByName('prmanBxdf'):
                    bxdf = terms.getChildByName('prmanBxdf').getValue('')

                if terms.getChildByName('prmanDisplacement'):
                    displacement = terms.getChildByName(
                                    'prmanDisplacement').getValue('')

                if terms.getChildByName('prmanDisplayfilter'):
                    displayfilter = terms.getChildByName(
                                    'prmanDisplayfilter').getValue('')
                    exportDisplayFilters = True

                # add root node and connections to the asset.  This isn't strictly
                # necessary, but it useful to validate which nodes are the terminal nodes
                if (displacement != '' or bxdf != '') and not exportDisplayFilters:
                    nodeClass = 'root'
                    rmanNode = 'shadingEngine'
                    nodeType = 'shadingEngine'
                    nodeName = '%s_SG' % Asset.label()
                    Asset.addNode(nodeName, nodeType,
                                    nodeClass, rmanNode,
                                    externalosl=False)
                    if bxdf != '':
                        infodict = {}
                        infodict['name'] = 'rman__surface'
                        infodict['type'] = 'reference float3'
                        infodict['value'] = None
                        Asset.addParam(nodeName, nodeType, 'rman__surface', infodict)

                        bxdfPort = ''
                        bxdfPortAttr = terms.getChildByName('prmanBxdfPort')
                        if bxdfPortAttr:
                            bxdfPort = bxdfPortAttr.getValue('')
                        dst = nodeName + '.' + infodict['name']
                        src = bxdf + '.' + bxdfPort
                        Asset.addConnection(src, dst)
                    if displacement != '':
                        infodict = {}
                        infodict['name'] = 'rman__displacement'
                        infodict['type'] = 'reference float3'
                        infodict['value'] = None
                        Asset.addParam(nodeName, nodeType, 'rman__displacement', infodict)

                        dispPort = ''
                        dispPortAttr = terms.getChildByName('prmanDisplacementPort')
                        if dispPortAttr:
                            dispPort = dispPortAttr.getValue('')
                        dst = nodeName + '.' + infodict['name']
                        src = displacement + '.' + dispPort
                        Asset.addConnection(src, dst)

            except:
                continue

            for childName, child in nodes.childList():
                try:
                    shaderType = child.getChildByName('type').getValue('')
                    nodeName = child.getChildByName('name').getValue('')
                    # TODO: Store the srcName for use on import.  The srcName should be
                    # the name of the PrmanShadingNode and childName is the name of the
                    # shading node sent to the renderer.
                    #
                    # srcName = child.getChildByName('srcName').getValue('')
                    #
                    # For now, use the childName to build the network because it is the
                    # ame used in the material attribute for terminals and connections.
                    srcName = childName
                    connections = child.getChildByName('connections')
                except:
                    continue
                shaderName = shaderType

                # ask for the RenderMan type via plug-in function
                shaderInfoAttr = FnGeolibServices.AttributeFunctionUtil.Run(
                                'PRManGetShaderInfo',
                                FnAttribute.StringAttribute(shaderType))
                shaderTypeTags = shaderInfoAttr.getChildByName('shaderTypeTags').getValue('')

                # only export display filters for display filter export
                if exportDisplayFilters:
                    if 'displayfilter' not in shaderTypeTags:
                        continue
                    if shaderType == 'PxrDisplayFilterCombiner':
                        continue

                vstructs = []

                externalosl = False
                shaderFullPath = shaderInfoAttr.getChildByName(
                                'shaderFullPath').getValue('')
                if (not shaderType.startswith("Pxr") and
                    os.path.splitext(shaderFullPath)[1] == '.oso'):
                    externalosl = True
                    # Register the oso file as a dependency that should be saved
                    # with the asset.
                    Asset.processExternalFile(None, ExternalFile.k_osl, shaderFullPath)

                if 'bxdf' in shaderTypeTags:
                    Asset.addNode(
                        nodeName, shaderName,
                        'bxdf', shaderName, externalosl)
                elif 'displacement' in shaderTypeTags:
                    Asset.addNode(
                        nodeName, shaderName,
                        'displace', shaderName, externalosl)
                elif 'displayfilter' in shaderTypeTags:
                    Asset.addNode(
                        nodeName, shaderName,
                        'displayfilter', shaderName, externalosl)
                else:
                    Asset.addNode(
                        nodeName, shaderName,
                        'pattern', shaderName, externalosl)

                try:
                    nodeParams = child.getChildByName('parameters')
                    shaderParams = shaderInfoAttr.getChildByName('params')
                    outputs = shaderInfoAttr.getChildByName('outputs')
                except:
                    continue

                for i in range(0, shaderParams.getNumberOfChildren()):
                    paramName = shaderParams.getChildName(i)

                    p = None
                    if nodeParams:
                        p = nodeParams.getChildByName(paramName)

                    typeVal = shaderParams.getChildByName(
                                            paramName + '.type').getValue()
                    defaultAttr = shaderParams.getChildByName(
                                            paramName + '.defaultAttr')
                    arraySize = shaderParams.getChildByName(
                                        paramName + '.arraySize').getValue()

                    reference = ''
                    isOutput = False
                    hasVstructMember = False
                    rman_type = 'float'
                    if typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypePoint3):
                        rman_type = 'point'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeColor3):
                        rman_type = 'color'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeVector3):
                        rman_type = 'vector'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeNormal):
                        rman_type = 'normal'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeMatrix):
                        rman_type = 'matrix'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeString):
                        rman_type = 'string'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeInt):
                        rman_type = 'int'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypePointer):
                        rman_type = 'struct'
                    elif typeVal == (
                                    RenderingAPI.RendererInfo.
                                    kRendererObjectValueTypeShader):
                        typeString = shaderParams.getChildByName(
                                paramName + '.hints.typeString')
                        if typeString is not None:
                            rman_type = typeString.getValue('struct')
                        else:
                            rman_type = 'struct'

                    tagAttr = shaderParams.getChildByName(
                                paramName + '.hints.tag')
                    if tagAttr is not None:
                        if tagAttr.getValue('') == 'vstruct':
                            rman_type = 'vstruct'
                            vstructs.append(paramName)

                    if paramName in outputs.getData():
                        isOutput = True

                    infodict = {}

                    vstructMemberAttr = shaderParams.getChildByName(
                                        paramName + '.hints.vstructmember')
                    if vstructMemberAttr is not None:
                        vstructMember = vstructMemberAttr.getValue('')
                        infodict['vstructmember'] = vstructMember
                        hasVstructMember = True
                        vstruct = vstructMember.split('.')[0]
                        if vstruct not in vstructs:
                            Asset.addParam(
                                nodeName, shaderName, vstruct,
                                {
                                    'type': 'reference vstruct',
                                    'value': None, 'default': ''})
                            vstructs.append(vstruct)

                    vstructCondAttr = shaderParams.getChildByName(
                                    paramName +
                                    '.hints.vstructConditionalExpr')
                    if vstructCondAttr is not None:
                        vstructCond = vstructCondAttr.getValue('')
                        infodict['vstructConditionalExpr'] = vstructCond
                        isOutput = True

                    value = None

                    if p is not None:
                        numTuples = p.getNumberOfTuples()

                        value = p.getData()
                        if rman_type not in _RMAN_FLOAT3_ and arraySize == 0:
                            value = value[0]
                    else:
                        numTuples = defaultAttr.getNumberOfTuples()

                    defaultVal = defaultAttr.getData()
                    if rman_type not in _RMAN_FLOAT3_ and arraySize == 0:
                        defaultVal = defaultVal[0]

                    infodict['name'] = paramName
                    if value is None or p is None:
                        rman_val = _sanitize_list(rman_type, defaultVal)
                        infodict['default'] = rman_val
                        infodict['value'] = rman_val
                    else:
                        rman_val = _sanitize_list(rman_type, value)
                        infodict['value'] = rman_val

                    # the param names in array connections are in the form "name:index"
                    if connections and paramName in [x[0].split(":")[0] for x in connections.childList()]:
                        reference = 'reference '
                        value = None
                        infodict['value'] = value

                        # number of connections in the array (if this is an array)
                        numTuples = len([x for x in connections.childList() if x[0].split(":")[0] == paramName])
                    else:
                        if rman_type == 'struct':
                            continue

                    if arraySize > 1 or arraySize == -1:
                        rman_type += '[' + str(numTuples) + ']'

                    if isOutput is True:
                        rman_type = 'output ' + rman_type

                    infodict['type'] = reference + rman_type
                    Asset.addParam(nodeName, shaderName, paramName, infodict)

                # Now do the connections.
                # Display filters are imported as a list and don't have connections
                if connections and not exportDisplayFilters:
                    for paramName, con in connections.childList():
                        val = con.getValue('')
                        srcParam = val.split('@')[0]
                        srcName = val.split('@')[1]

                        if ':' in paramName:
                            p = paramName.split(':')[0]
                            idx =  paramName.split(':')[1]
                            paramName = p + '[' + idx + ']'

                        dst = nodeName + '.' + paramName
                        src = srcName + '.' + srcParam
                        Asset.addConnection(src, dst)


# @brief      Builds a filename from the asset label string
#
# @param      label  User-friendly label
#
# @return     the asset file name
#
def asset_name_from_label(label):
    assetDir = re.sub('[^\w]', '', re.sub(' ', '_', label)) + '.rma'
    return assetDir


def parse_texture(imagePath, Asset):
    """Gathers infos from the image header

    Arguments:
        imagePath {list} -- A list of texture paths.
        Asset {RmanAsset} -- the asset in which the infos will be stored.
    """
    img = FilePath(imagePath)
    # gather info on the envMap
    #
    Asset.addTextureInfos(img)


def get_color_config():
    """Return a ocio config dict based on current OCIO configuration."""
    ocio_file = os.environ.get('OCIO', None)
    color_mgr = ColorManager(ocio_file)
    ocio_config = {
        'config': color_mgr.cfg_name,
        'path': color_mgr.config_file_path(),
        'rules': color_mgr.conversion_rules,
        'aliases': color_mgr.aliases
    }
    logging.debug('ocio_config %s', '=' * 80)
    logging.debug('     config = %s', ocio_config['config'])
    logging.debug('       path = %s', ocio_config['path'])
    logging.debug('      rules = %s', ocio_config['rules'])
    return ocio_config


def export_asset(
            nodes, atype, infodict,
            category, cfg, renderPreview='std',
            alwaysOverwrite=False, isLightRig=False):
    """Exports a nodeGraph or envMap as a RenderManAsset.

    Arguments:
        nodes {list} -- nodes to export
        atype {str} -- Asset type : 'nodeGraph' or 'envMap'
        infodict {dict} -- dict with 'label', 'author' & 'version'
        category {str} -- Category as a path, i.e.: "/Lights/LookDev"

    Keyword Arguments:
        renderPreview {str} -- Render an asset preview ('std', 'fur', None).\
                        Render the standard preview swatch by default.\
                        (default: {'std'})
        alwaysOverwrite {bool} -- Will ask the user if the asset already \
                        exists when not in batch mode. (default: {False})
    """
    aa = infodict.get('storage').getValue()

    label = infodict['label']
    Asset = RmanAsset(assetType=atype, label=label, previewType=renderPreview,
                      storage=infodict.get('storage', None),
                      convert_to_tex=infodict.get('convert_to_tex', True))

    # On save, we can get the current color manager to store the config.
    Asset.ocio = get_color_config()

    # Add user metadata
    #
    for k, v in infodict['metadata'].items():
        Asset.addMetadata(k, v)

    # Compatibility data
    # This will help other application decide if they can use this asset.
    #
    prmanVersion = _RMANVERSION_
    katanaVersion = _KATANAVERSION_
    Asset.setCompatibility(hostName='Katana',
                           hostVersion=katanaVersion,
                           rendererVersion=prmanVersion)

    # parse Katana scene
    #
    if atype is "nodeGraph":
        parse_node_graph(nodes, Asset, isLightRig)
    elif atype is "envMap":
        parse_texture(nodes[0], Asset)
    else:
        raise RmanAssetKatanaError("%s is not a known asset type !" % atype)
        return False

    #  Get path to our library
    #
    assetPath = ral.getAbsCategoryPath(cfg, category)

    #  Create our directory
    #
    assetDir = asset_name_from_label(str(label))
    dirPath = assetPath.join(assetDir)
    if not dirPath.exists():
        os.mkdir(dirPath)

    #   Check if we are overwriting an existing asset
    #
    jsonfile = dirPath.join("asset.json")
    if jsonfile.exists():
        if alwaysOverwrite:
            print('Replacing existing file : %s' % jsonfile)
        else:
            return False

    #  Save our json file
    #
    # print("exportAsset: %s..." %   dirPath)
    Asset.save(jsonfile, compact=False)
    return True


def import_asset(filepath, assignToSelected):

    # early exit
    if not os.path.exists(filepath):
        raise RmanAssetKatanaError("File doesn't exist: %s" % filepath)

    Asset = RmanAsset()
    Asset.load(filepath, localizeFilePaths=True)
    assetType = Asset.type()

    # compatibility check
    #
    # if not compatibilityCheck(Asset):
    #    return

    if assetType == "nodeGraph":
        path = os.path.dirname(Asset.path())
        paths = path.split('/')
        if 'Materials' in paths:
            if Asset.displayFilterList():
                # create display filter nodes
                create_displayFilters(Asset, assignToSelected)

            if Asset.nodeList():
                # create material nodes
                nodeDict = {}
                nodeDict, nodeList, networkMtlNode = create_nodes(Asset, assignToSelected)
                connect_nodes(Asset, nodeDict, nodeList, networkMtlNode)

        elif 'LightRigs' in paths:
            import_light_rig(Asset)
        else:
            raise RmanAssetKatanaError('nodeGraph type not supported.')

    elif assetType == "envMap":
        import_envmap(Asset)
    else:
        raise RmanAssetKatanaError('Unknown asset type: %s' % assetType)

    return ''


def get_light_nodes():

    sel = []

    sg = UI4.App.Tabs.FindTopTab('Scene Graph')
    sgv = sg.getSceneGraphView()
    lightName = None
    for si in sgv.getSelectedItems():
        if si.getLocationType() == 'light':
            lightName = si.getLocationPath()
            sel.append(lightName)

    return sel


def default_label_from_filename(filename):
    # print filename
    lbl = os.path.splitext(os.path.basename(filename))[0]
    # print lbl
    lbl = re.sub('([A-Z]+)', r' \1', lbl)
    # print lbl
    lbl = lbl.replace('_', ' ')
    return lbl.strip().capitalize()


# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------

PrefsGroupKey = 'PrmanPresetBrowser'

KatanaHostPrefs = None
def GetKatanaHostPrefsClass():
    global KatanaHostPrefs
    if KatanaHostPrefs is not None:
        return

    class KatanaHostPrefsClass(ral.HostPrefs):

        def __init__(self):
            super(KatanaHostPrefsClass, self).__init__(_RMANVERSION_)
            self.debug = False

            self.InstallPresetBrowserGroupPreference()
            self.hostTree = ''
            self.rmanTree = os.environ['RMANTREE']


            # === Library Prefs ===
            #
            self.rpbConfigFile = FilePath(self.getHostPref('rpbConfigFile', ''))
            # the list of user libraries from Maya prefs
            self.rpbUserLibraries = self.getHostPref('rpbUserLibraries', [])
            # We don't initialize the library configuration just yet. We want
            # to do it only once the prefs objects has been fully contructed.
            # This is currently done in rmanAssets.ui.Ui.__init__()
            self.cfg = None

            # === UI Prefs ===
            #
            # our prefered swatch size in the UI.
            self.rpbSwatchSize = self.getHostPref('rpbSwatchSize', 64)
            # the last selected preview type
            self.rpbSelectedPreviewEnv = self.getHostPref(
                'rpbSelectedPreviewEnv', 0)
            # the last selected category
            self.rpbSelectedCategory = self.getHostPref('rpbSelectedCategory', '')
            # the last selected library
            self.rpbSelectedLibrary = FilePath(self.getHostPref(
                'rpbSelectedLibrary', ''))
            self.rpbStorageMode = self.getHostPref('rpbStorageMode', 0)
            self.rpbStorageKey = self.getHostPref('rpbStorageKey', '')
            self.rpbStoragePath = self.getHostPref('rpbStoragePath', '')
            self.rpbConvertToTex = self.getHostPref('rpbConvertToTex', True)
            if self.debug:
                print ('KatanaPrefs init:')
                print ('  rpbConfigFile: %s' % self.rpbConfigFile)
                print ('  rpbUserLibraries: %s' % self.rpbUserLibraries)
                print ('  rpbSelectedCategory: %s' % self.rpbSelectedCategory)
                print ('  rpbSelectedLibrary: %s' % self.rpbSelectedLibrary)
                print ('  rpbStorageMode: %s' % self.rpbStorageMode)
                print ('  rpbStorageKey: %s' % self.rpbStorageKey)
                print ('  rpbStoragePath: %s' % self.rpbStoragePath)
                print ('  rpbConvertToTex: %s' % self.rpbConvertToTex)

            # === User Prefs ===
            #
            # render all HDR environments ?
            self.rpbRenderAllHDRs = self.getHostPref('rpbRenderAllHDRs', False)
            self.rpbHideFactoryLib = self.getHostPref('rpbHideFactoryLib', False)

            self.selectedSgLightNodes = []
            self.selectedSgMaterialNode = None

        # Not used, but needed if we want to expose our preferences to the UI
        def on_pref_changed(self, *args, **kwargs):
            return
            # if kwargs.get('prefKey','') == PrefsLibraryPathKey:
            #   do somthing

        def InstallPresetBrowserGroupPreference(self):
            '''
            Registers the 'PresetBrowser' group preference with
            the Preferences core and UI.
            '''
            # Register preferences
            # If we want to expose the preferences in the UI, set visible=True
            KatanaPrefs.declareGroupPref(PrefsGroupKey, visible=False, hints=None)

            # Register an event handler to catch updates to preferences
            # Utils.EventModule.RegisterEventHandler( self.on_pref_changed,
            #                                    'pref_changed', enabled=True)

        def registerPref(self, pref, defaultValue):

            prefName = PrefsGroupKey + '/' + pref
            if prefName not in KatanaPrefs.keys():
                prefName = PrefsGroupKey + '/' + pref
                if isinstance(defaultValue, str) or (
                                                    isinstance(
                                                                defaultValue,
                                                                str)):
                    KatanaPrefs.declareStringPref(prefName, defaultValue, prefName)
                elif isinstance(defaultValue, list):
                    if not defaultValue:
                        KatanaPrefs.declareStringPref(prefName, '', prefName)
                    else:
                        val = ':'.join(defaultValue)
                        KatanaPrefs.declareStringPref(prefName, val, prefName)
                elif isinstance(defaultValue, bool):
                    KatanaPrefs.declareBoolPref(prefName, defaultValue, prefName)
                elif isinstance(defaultValue, int):
                    KatanaPrefs.declareIntPref(prefName, defaultValue, prefName)
                elif isinstance(defaultValue, bool):
                    KatanaPrefs.declareBoolPref(prefName, defaultValue, prefName)
                elif isinstance(defaultValue, float):
                    KatanaPrefs.declareDoublePref(prefName, defaultValue, prefName)
                else:
                    pass

        def getHostPref(self, pref, defaultValue):
            """Reads a single pref from the host application.

            Args:
                prefName (str): The preference name
                defaultValue (any): A default value if the pref does not exist yet.

            Returns:
                int/str/str[]: The current value or the default if not available.
            """

            self.registerPref(pref, defaultValue)

            V = defaultValue
            prefName = PrefsGroupKey + '/' + pref
            if prefName in KatanaPrefs.keys():
                if isinstance(defaultValue, list):
                    if KatanaPrefs[prefName] == '':
                        V = []
                    else:
                        V = KatanaPrefs[prefName].split(':')
                else:
                    V = KatanaPrefs[prefName]

            return V

        def setHostPref(self, pref, value):
            """Save the given value in the host's preferences.
            First look at the value's type and call the matching host API. In Maya,
            this is maya.cmds.optionVar. The optionVar is named after the class
            attribute.

            Args:
                prefName (str): The class attribute name for that pref.
                value (int/str/str[]): The value we should store.

            Raises:
                RmanAssetKatanaError: If we don't support the given data type.
            """
            prefName = PrefsGroupKey + '/' + pref
            if prefName in KatanaPrefs.keys():
                if isinstance(value, list):
                    if not value:
                        KatanaPrefs[prefName] = ''
                    else:
                        KatanaPrefs[prefName] = ':'.join(value)
                elif isinstance(value, FilePath):
                    KatanaPrefs[prefName] = str(value)
                else:
                    KatanaPrefs[prefName] = value

            KatanaPrefs.commit()

        def saveAllPrefs(self):
            # === Library Prefs ===
            self.setHostPref('rpbConfigFile', self.rpbConfigFile)
            self.setHostPref('rpbSelectedLibrary', self.rpbSelectedLibrary)
            self.setHostPref('rpbUserLibraries', self.rpbUserLibraries)
            self.setHostPref('rpbStorageMode', self.rpbStorageMode)
            self.setHostPref('rpbStorageKey', self.rpbStorageKey)
            self.setHostPref('rpbStoragePath', self.rpbStoragePath)
            self.setHostPref('rpbConvertToTex', self.rpbConvertToTex)
            # === UI Prefs ===
            self.setHostPref('rpbSwatchSize', self.rpbSwatchSize)
            self.setHostPref('rpbSelectedPreviewEnv', ral.getPreviewHdrIdx())
            self.setHostPref('rpbSelectedCategory', self.rpbSelectedCategory)
            # === User Prefs ===
            self.setHostPref('rpbRenderAllHDRs', self.rpbRenderAllHDRs)
            self.setHostPref('rpbHideFactoryLib', self.rpbHideFactoryLib)
            if self.debug:
                print('>> preset browser prefs saved')

        def doAssign(self):
            # True if we support assigning a material to geometry
            return True

        def preExportCheck(self, mode, hdr=None):
            if mode == 'material':
                nwMatName = None
                if self.selectedSgMaterialNode is None:
                    sg = UI4.App.Tabs.FindTopTab('Scene Graph')
                    sgv = sg.getSceneGraphView()
                    for si in sgv.getSelectedItems():
                        if si.getLocationType() == 'material':
                            nwMatName = si.getLocationPath()
                            break
                    if nwMatName is None:
                        return False
                else:
                    nwMatName = self.selectedSgMaterialNode

                sel = {}
                sel[nwMatName] = ''

                self._nodesToExport = sel
                self._defaultLabel = os.path.basename(nwMatName)
                self.selectedSgNode = None
                return (self._nodesToExport != {})
            elif mode == 'lightrigs':
                if not self.selectedSgLightNodes:
                    self._nodesToExport = get_light_nodes()
                else:
                    self._nodesToExport = self.selectedSgLightNodes

                if self._nodesToExport == []:
                    return False
                firstNode = self._nodesToExport[0]
                self._defaultLabel = os.path.basename(firstNode)
                return (self._nodesToExport != [])
            elif mode == 'envmap':
                if not hdr.exists():
                    return False
                self._nodesToExport = [hdr]
                self._defaultLabel = default_label_from_filename(hdr)
                return True
            else:
                return False
            return False

        def exportMaterial(self, categorypath, infodict, previewtype):
            return export_asset(
                self._nodesToExport, 'nodeGraph', infodict,
                categorypath, self.cfg, renderPreview=previewtype,
                alwaysOverwrite=True, isLightRig=False)

        def exportLightRig(self, categorypath, infodict):
            return export_asset(
                self._nodesToExport, 'nodeGraph', infodict,
                categorypath, self.cfg, renderPreview='std',
                alwaysOverwrite=True, isLightRig=True)

        def exportEnvMap(self, categorypath, infodict):
            print categorypath
            print infodict
            return export_asset(self._nodesToExport, 'envMap', infodict, categorypath,
                        self.cfg)

        def importAsset(self, asset, assignToSelected=False):
            import_asset(asset.jsonFilePath(), assignToSelected)

        def setSelectedSgMaterialNode(self, selected):

            self.selectedSgMaterialNode = selected

        def setSelectedSgLightNodes(self, selected):

            self.selectedSgLightNodes = selected

    KatanaHostPrefs = KatanaHostPrefsClass
    


class KJS_PrmanPresetBrowser(UI4.Tabs.BaseTab):

    def __init__(self, parent):
        UI4.Tabs.BaseTab.__init__(self, parent)     
        self.hostPrefs = None


        _Initialize()

        if _RMANVERSION_:
            self.hostPrefs = KatanaHostPrefs()
            self.ui = rui.Ui(self.hostPrefs, parent=self)
            self.setLayout(self.ui.topLayout)
            self.setAcceptDrops(True)


        else:
            QHBoxLayout(self)
            self.layout().addWidget(QLabel('RMANTREE not set.', self))
            
########################################################################################## 
#

        self.add_menu = self.ui.menuBar.addMenu('WW')      
        self.create_envmap_action = QtWidgets.QAction('Create Env Map', self.add_menu)
        self.add_menu.addAction(self.create_envmap_action)               
        self.create_envmap_action.triggered.connect(self.create_envmap)        
        
        self.tree_widget = self.findChild(QtWidgets.QTreeWidget)        
        self.tree_widget.itemChanged.connect(self.change_treewidget_buttons)    
        
        
    def create_envmap(self):                        
        win = create_image_package_run.Widget()
        status, info_dict = win.showModal()
        
        self.ui.assetList.update()         
        self.setup_event_filters()
        
        
    def change_treewidget_buttons(self, item, column):
        print 'change_buttons'
        if column == 0:
            if item.childCount() > 0:
                parent_check_state = item.checkState(column)
                for i in range(item.childCount()):
                    item.child(i).setCheckState(column, parent_check_state)

                    self.tree_widget.blockSignals(True)

                    if item.checkState(0) == QtCore.Qt.Checked:

                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
                    else:

                        item.setFlags(item.flags() | QtCore.Qt.ItemIsSelectable)
                
                    self.tree_widget.blockSignals(False)   
                    
#     
########################################################################################## 


    def closeEvent(self, event):
        if self.hostPrefs is not None:
            self.hostPrefs.saveAllPrefs()

    def saveUIGeometry(self):
        return

    def updateUI(self, reset=False):
        self.ui.updateUI(reset)

                    
##########################################################################################     
#

    def setup_event_filters(self):
        for child in self.findChildren(QtWidgets.QWidget):
            child.installEventFilter(self)
    
        
    def add_action_menu(self, widget, event):
        print 'add_menu' 
        # 위젯 스택이 계속 쌓이는 이슈때문에 지웠다 생성하기
        for child in widget.children():
            if isinstance(child, QtWidgets.QMenu):
                child.deleteLater()
        
        add_nemu = QtWidgets.QMenu(widget)        
        bb_action = QtWidgets.QAction('bb', self)
        add_nemu.addAction(bb_action)        
        add_nemu.exec_(event.globalPos())   
        
                
    def swatch_override_menu(self, pos):
        print 'swatch_nemu'       
        swatch_nemu = QtWidgets.QMenu()      
          
        preview_action = QtWidgets.QAction('Show Preview', self)
        preview_action.triggered.connect(self.show_preview)
        swatch_nemu.addAction(preview_action)  
        open_prman_action = QtWidgets.QAction('Open Prman', self)
        open_prman_action.triggered.connect(lambda: self.open_folder('prman'))
        swatch_nemu.addAction(open_prman_action)         
        open_library_action = QtWidgets.QAction('Open Library', self)
        open_library_action.triggered.connect(lambda: self.open_folder('library'))
        swatch_nemu.addAction(open_library_action)                              
        sep_line_01 = QtWidgets.QAction(' ', self)
        sep_line_01.setSeparator(True)            
        swatch_nemu.addAction(sep_line_01)              

        update_mata_action = QtWidgets.QAction('Update Metadata', self)
        update_mata_action.triggered.connect(self.update_mata)
        swatch_nemu.addAction(update_mata_action)       
        change_category_action = QtWidgets.QAction('Change Category', self)
        change_category_action.triggered.connect(self.change_category)
        swatch_nemu.addAction(change_category_action)         
        rename_action = QtWidgets.QAction('Rename', self)
        rename_action.triggered.connect(self.swatch_rename)
        swatch_nemu.addAction(rename_action)                 
        sep_line_02 = QtWidgets.QAction(' ', self)
        sep_line_02.setSeparator(True)            
        swatch_nemu.addAction(sep_line_02)                  
        
        preview_action = QtWidgets.QAction('Delete', self)
        swatch_nemu.addAction(preview_action)  
        
        del_memu = QtWidgets.QMenu()      
        delete_all_action = QtWidgets.QAction('Delete All', self)
        delete_all_action.triggered.connect(self.delete_all)
        del_memu.addAction(delete_all_action)              
        preview_action.setMenu(del_memu)               
        
        swatch_nemu.exec_(pos)
        
        
    def show_preview(self):   
        all_swatch = self.ui.swatches        
        sel_swatch = self.ui.selectedSwatch        
 
        preview_widget = preview_widget_run.Widget(all_swatch, sel_swatch)
        preview_widget.ui.show()
 
    def delete_all(self):    
        sel_swatch = self.ui.selectedSwatch        
        point_x = self.pos().x() + self.rect().width()//2 - 100
        point_y = self.pos().y() + self.rect().height()//2 - 100            
        adjusted_pos = QtCore.QPoint(point_x, point_y)              
        browser_add_func.delete_all_path(adjusted_pos, sel_swatch)
        
        self.ui.assetList.update()  
        self.setup_event_filters()
        
        
    def open_folder(self, name):
        sel_swatch = self.ui.selectedSwatch            
        browser_add_func.open_folder(sel_swatch, name)     
        
        
    def change_category(self):
        sel_swatch = self.ui.selectedSwatch   
        point_x = self.pos().x() + self.rect().width()//2 - 100
        point_y = self.pos().y() + self.rect().height()//2 - 100            
        adjusted_pos = QtCore.QPoint(point_x, point_y)               
        
        win = cetegory_func.UpdateCategory(adjusted_pos, sel_swatch)
        status = win.showModal()      
        
        self.ui.assetList.update()
        self.setup_event_filters()    
        

    def update_mata(self):
        sel_swatch = self.ui.selectedSwatch   
        point_x = self.pos().x() + self.rect().width()//2 - 100
        point_y = self.pos().y() + self.rect().height()//2 - 100            
        adjusted_pos = QtCore.QPoint(point_x, point_y)               
        
        win = metadata_func.UpdateMeta(adjusted_pos, sel_swatch)
        status = win.showModal()      
        
        self.ui.assetList.update()
        self.setup_event_filters()    
        
    def swatch_rename(self):    
        sel_swatch = self.ui.selectedSwatch   
        point_x = self.pos().x() + self.rect().width()//2 - 100
        point_y = self.pos().y() + self.rect().height()//2 - 100            
        adjusted_pos = QtCore.QPoint(point_x, point_y)               
        
        win = browser_add_func.RenameSwatch(adjusted_pos, sel_swatch)
        status, name = win.showModal()      

        self.ui.assetList.update()
        self.ui.assetList.selectSwatchByLabel(name)        
        self.setup_event_filters()


    def swatch_double_click(self, event):
        get_gaffers = NodegraphAPI.GetAllNodesByType('GafferThree')
        json_path = self.ui.selectedSwatch._asset.jsonFilePath()
                
        create_gaffer_modules.create_item_in_gaffer('prman', get_gaffers, json_path, self)

       
    def eventFilter(self, obj, event):      
        # Swatch 오브젝트 관련 
        if 'ui_buttons.Swatch' in str(type(obj)):
            #self.setup_event_filters()
            if event.type() == QtCore.QEvent.MouseButtonPress:
                # 드래그 포지션 값 추출            
                if event.button() == QtCore.Qt.LeftButton: 
                    obj._drag_start_position = event.pos() 
                    
                # 마우스 오른쪽 메뉴바 오버라이드                                                
                if event.button() == QtCore.Qt.RightButton:
                    obj._showMenu = self.swatch_override_menu.__get__(obj)     
                    event.accept()
                    return True   

            # 마우스 더블클릭 오버라이드            
            elif event.type() == QtCore.QEvent.MouseButtonDblClick:
                if event.button() == QtCore.Qt.LeftButton:
                    if 'ui_buttons.Swatch' in str(type(obj)):
                        obj.mouseDoubleClickEvent = self.swatch_double_click.__get__(obj)
                        event.accept()

                   
            # 드래그 앤 드랍                        
            elif event.type() == QtCore.QEvent.MouseMove: 
                # 드래그를 시작하기 위해서는 최소거리 이동을 해야한다.
                if event.buttons() & QtCore.Qt.LeftButton: 
                    if (event.pos() - obj._drag_start_position).manhattanLength() < QtWidgets.QApplication.startDragDistance(): 
                        return False
                        
                drag = QtGui.QDrag(obj) 
                mime_data = QtCore.QMimeData() 
                # 나중에 여기서 데이터 교체하면 될듯
                mime_data.setText(obj.text()) 
                drag.setMimeData(mime_data) 

                # 드래그시 이미지 생성
                pixmap = obj.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(event.pos() - obj.rect().topLeft())
                
                drag.exec_(QtCore.Qt.MoveAction) 
                
            elif event.type() == QtCore.QEvent.DragEnter: 
                if event.mimeData().hasText(): 
                    event.acceptProposedAction()
                    
            elif event.type() == QtCore.QEvent.Drop: 
                if event.mimeData().hasText(): 
                    obj.setText(event.mimeData().text()) 
                    event.acceptProposedAction() 
    

        # Swatch에 대한 배경 위젯
        elif obj.objectName() == 'scrollbg':
            if event.type() == QtCore.QEvent.MouseButtonRelease: 
                # 마우스 오른쪽 메뉴바 추가
                if event.button() == QtCore.Qt.RightButton and type(obj) == QtWidgets.QScrollArea:
                    self.add_action_menu(obj, event)
                    event.accept()   
     
        # 카테고리 이동시 이벤트필터 재맵핑이슈
        elif obj.objectName() == 'qt_scrollarea_viewport':  
            if event.type() == QtCore.QEvent.MouseButtonRelease:         
                self.setup_event_filters()
                event.accept()            
            
            
        return super(KJS_PrmanPresetBrowser, self).eventFilter(obj, event)                    
                
#                
##########################################################################################         

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('scenegraph/paths'):
            data = bytes(e.mimeData().data('scenegraph/paths')).decode('UTF-8')
            droppedPaths = data.split(' ')
            viewNode = NodegraphAPI.GetViewNode()
            producer = Nodes3DAPI.GetGeometryProducer(node=viewNode)
            foundAny = False
            for path in droppedPaths:
                prod = producer.getProducerByPath(path)
                if prod is None:
                    continue
                if prod.getType() == 'material':
                    foundAny = True
                    break
                elif prod.getType() == 'light':
                    foundAny = True
                    break
            if foundAny:
                e.accept()
            else:
                # do one more check by recursing down
                materials = []
                lights = []
                for path in droppedPaths:
                    prod = producer.getProducerByPath(path)
                    if prod is None:
                        continue
                    self.recurseDownSceneGraphForMaterials(
                                        materials, prod, path)
                    self.recurseDownSceneGraphForLights(lights, prod, path)

                if (materials is not None) or (lights is not None):
                    e.accept()
                else:
                    e.ignore()
        else:
            e.ignore()

    def recurseDownSceneGraphForLights(self, lights, producer, path):

        for child in producer.iterChildren():
            child_path = path + '/' + child.getName()
            if child.getType() == 'light':
                lights.append(child_path)
            self.recurseDownSceneGraphForLights(lights, child, child_path)

    def recurseDownSceneGraphForMaterials(self, materials, producer, path):

        for child in producer.iterChildren():
            child_path = path + '/' + child.getName()
            if child.getType() == 'material':
                materials.append(child_path)
            self.recurseDownSceneGraphForMaterials(
                    materials, child, child_path)

    def dropEvent(self, e):
        if e.mimeData().hasFormat('scenegraph/paths'):
            e.accept()
            data = bytes(e.mimeData().data('scenegraph/paths')).decode('UTF-8')
            droppedPaths = data.split(' ')
            materials = []
            lights = []
            viewNode = NodegraphAPI.GetViewNode()
            producer = Nodes3DAPI.GetGeometryProducer(node=viewNode)
            for path in droppedPaths:
                prod = producer.getProducerByPath(path)
                if prod is None:
                    continue
                if prod.getType() == 'material':
                    materials.append(path)
                elif prod.getType() == 'light':
                    lights.append(path)

            if not materials and not lights:
                for path in droppedPaths:
                    prod = producer.getProducerByPath(path)
                    if prod is None:
                        continue
                    self.recurseDownSceneGraphForMaterials(
                                        materials, prod, path)
                    self.recurseDownSceneGraphForLights(lights, prod, path)

                if materials:
                    for mat in materials:
                        self.hostPrefs.setSelectedSgMaterialNode(mat)
                        self.ui.newMaterial()

                if lights:
                    self.hostPrefs.setSelectedSgLightNodes(lights)
                    self.ui.newLightRig()

            else:
                if materials:
                    for mat in materials:
                        self.hostPrefs.setSelectedSgMaterialNode(mat)
                        self.ui.newMaterial()

                if lights:
                    self.hostPrefs.setSelectedSgLightNodes(lights)
                    self.ui.newLightRig()
        else:
            e.ignore()
            
            

   

PluginRegistry = [
    ('KatanaPanel', 2.0, 'PrmanPresetBrowser_Sample', KJS_PrmanPresetBrowser),
]
