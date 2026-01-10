document.addEventListener('DOMContentLoaded', function() {
    // ============================================================================
    // DOM ELEMENT REFERENCES
    // ============================================================================
    
    // Search and selection elements
    var searchInput = document.getElementById('search-input');
    var dropdownList = document.getElementById('dropdown-list');
    var selectedNodesDiv = document.getElementById('selected-nodes');
    var selectedPartitionsDiv = document.getElementById('selected-partitions');
    var searchResults = document.getElementById('search-results');
    var btnClear = document.getElementById('btn-clear');
    var toggleBtn = document.getElementById('toggle-btn');
    var searchContent = document.getElementById('search-content');
    
    // Edge type filter checkboxes
    var edgeCheckboxes = {
        letEdges: document.getElementById('show-let-edges'),
        implicationEdges: document.getElementById('show-implication-edges'),
        cauByCauEdges: document.getElementById('show-caubycau-edges'),
        cauBySupEdges: document.getElementById('show-caubysup-edges')
    };
    
    // Filter controls
    var edgeDirectionRadios = document.getElementsByName('edge-direction');
    var filterModeRadios = document.getElementsByName('filter-mode');
    
    // Dropdown items
    var checkboxItems = dropdownList.querySelectorAll('.checkbox-item');
    var checkboxes = dropdownList.querySelectorAll('input[type="checkbox"]');
    
    // Partition controls
    var partitionList = document.getElementById('partition-list');
    var partitionSearchInput = document.getElementById('partition-search-input');
    var partitionCheckboxes = partitionList ? partitionList.querySelectorAll('.partition-checkbox') : [];
    var partitionItems = partitionList ? partitionList.querySelectorAll('.checkbox-item') : [];
    
    // State
    var selectedNodes = new Set();
    var selectedPartitions = new Set();
    
    // ============================================================================
    // HELPER FUNCTIONS
    // ============================================================================
    
    var isEdgeHidden = function(edge) {
        return GraphEdges.isEdgeHiddenByTypeFilter(edge, edgeCheckboxes);
    };
    
    var updateSelectedDisplay = function() {
        GraphUIState.updateSelectedNodesDisplay(selectedNodesDiv, selectedNodes, checkboxes, updateSelectedDisplay, highlightNodes);
        GraphUIState.updateSelectedPartitionsDisplay(selectedPartitionsDiv, selectedPartitions, partitions, partitionLabels, partitionCheckboxes, updateSelectedDisplay, highlightNodes);
        GraphControlState.updatePartitionModeControls(selectedPartitions, selectedNodes, edgeCheckboxes, searchInput, checkboxes, checkboxItems, partitionSearchInput, partitionCheckboxes, partitionItems);
    };
    
    var highlightNodes = function() {
        var updateRankingsCallback = function() {
            GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
        };
        GraphHighlighting.highlightNodes(network, selectedPartitions, selectedNodes, partitions, filterModeRadios, edgeDirectionRadios, isEdgeHidden, searchResults, checkboxes, updateRankingsCallback);
    };
    
    var handleEdgeVisibilityUpdate = function() {
        var filterDropdownCallback = function(connectedNodes) {
            GraphNodes.filterDropdownByVisibility(network, connectedNodes, searchInput, checkboxItems);
        };
        var updateRankingsCallback = function() {
            GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
        };
        GraphEdges.handleEdgeVisibilityUpdate(network, selectedPartitions, selectedNodes, partitions, isEdgeHidden, highlightNodes, filterDropdownCallback, updateRankingsCallback);
    };
    
    var updateFilterModeControls = function() {
        GraphControlState.updateFilterModeControls(filterModeRadios, edgeDirectionRadios);
    };
    
    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    // Clear all selections when network is ready
    network.once('stabilizationIterationsDone', function() {
        network.selectNodes([]);
        network.selectEdges([]);
        network.unselectAll();
    });
    
    // ============================================================================
    // EVENT HANDLERS SETUP
    // ============================================================================
    
    // Edge type toggles
    GraphEdges.setupEdgeTypeHandlers(edgeCheckboxes, handleEdgeVisibilityUpdate);
    
    // Edge direction and filter mode
    GraphEventHandlers.setupEdgeDirectionHandlers(edgeDirectionRadios, selectedNodes, highlightNodes);
    GraphEventHandlers.setupFilterModeHandlers(filterModeRadios, selectedNodes, selectedPartitions, updateFilterModeControls, highlightNodes);
    
    // Toggle button
    GraphEventHandlers.setupToggleButtonHandler(toggleBtn, searchContent);
    
    // Search handlers
    GraphEventHandlers.setupSearchHandlers(searchInput, checkboxItems, network, isEdgeHidden);
    GraphEventHandlers.setupPartitionSearchHandler(partitionSearchInput, partitionItems);
    
    // Checkbox handlers
    GraphEventHandlers.setupNodeCheckboxHandlers(checkboxes, selectedNodes, updateSelectedDisplay, highlightNodes);
    GraphEventHandlers.setupPartitionCheckboxHandlers(partitionCheckboxes, selectedPartitions, updateSelectedDisplay, highlightNodes);
    
    // Item click handlers
    GraphEventHandlers.setupItemClickHandlers(checkboxItems);
    GraphEventHandlers.setupPartitionItemClickHandlers(partitionItems);
    
    // Clear button
    GraphEventHandlers.setupClearButtonHandler(btnClear, selectedNodes, selectedPartitions, checkboxes, partitionCheckboxes, updateSelectedDisplay, searchResults, searchInput, checkboxItems, handleEdgeVisibilityUpdate);
    
    // Leaf/Source node selections
    GraphNodes.setupLeafSourceNodeHandlers(leafNodeNames, sourceNodeNames, checkboxes, selectedNodes, updateSelectedDisplay, highlightNodes);
    
    // SCC controls
    var sccToggle = document.getElementById('scc-toggle');
    GraphEventHandlers.setupSCCHandler(sccToggle, sccs, network);
    
    // Rankings widget
    var rankingsToggleBtn = document.getElementById('rankings-toggle-btn');
    var rankingsContent = document.getElementById('rankings-content');
    var rankingsHeader = document.getElementById('rankings-header');
    GraphEventHandlers.setupRankingsToggle(rankingsToggleBtn, rankingsContent, rankingsHeader);
    
    // ============================================================================
    // INITIALIZATION - DEFAULT STATE
    // ============================================================================
    
    // Clear all selections
    selectedNodes.clear();
    selectedPartitions.clear();
    checkboxes.forEach(function(cb) { cb.checked = false; });
    partitionCheckboxes.forEach(function(cb) { cb.checked = false; });
    searchInput.value = '';
    if (partitionSearchInput) partitionSearchInput.value = '';
    searchResults.textContent = '';
    
    // Clear leaf/source node selections
    var selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
    var selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
    if (selectLeafNodesCheckbox) selectLeafNodesCheckbox.checked = false;
    if (selectSourceNodesCheckbox) selectSourceNodesCheckbox.checked = false;
    
    // Set default edge type visibility
    if (edgeCheckboxes.letEdges) edgeCheckboxes.letEdges.checked = true;
    if (edgeCheckboxes.implicationEdges) edgeCheckboxes.implicationEdges.checked = true;
    if (edgeCheckboxes.cauByCauEdges) edgeCheckboxes.cauByCauEdges.checked = true;
    if (edgeCheckboxes.cauBySupEdges) edgeCheckboxes.cauBySupEdges.checked = true;
    
    // Set default edge direction
    edgeDirectionRadios.forEach(function(radio) {
        if (radio.value === 'both') radio.checked = true;
    });
    
    // Initialize edge direction availability based on filter mode
    updateFilterModeControls();
    
    // Initialize display and rankings
    updateSelectedDisplay();
    GraphRankings.updateRankings(network, selectedNodes, checkboxes, isEdgeHidden);
});
