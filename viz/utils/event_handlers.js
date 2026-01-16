/**
 * Event Handlers Setup
 * Centralizes all event handler registration
 */

var GraphEventHandlers = (function() {
    'use strict';
    
    function setupSearchHandlers(searchInput, checkboxItems, network, isEdgeHidden) {
        searchInput.addEventListener('input', function() {
            var filter = this.value.toLowerCase();
            var connectedNodes = GraphNodes.getVisibleNodesFromEdges(network, isEdgeHidden);
            
            var allNodes = network.body.data.nodes.get();
            var visibleNodeNames = new Set();
            allNodes.forEach(function(node) {
                if (connectedNodes.has(node.id)) {
                    visibleNodeNames.add(GraphNodes.getNodeName(node.id));
                }
            });
            
            checkboxItems.forEach(function(item) {
                var checkbox = item.querySelector('input[type="checkbox"]');
                var label = item.querySelector('label').textContent.toLowerCase();
                var isVisible = visibleNodeNames.has(checkbox.value);
                item.style.display = (label.includes(filter) && isVisible) ? 'flex' : 'none';
            });
        });
    }
    
    function setupPartitionSearchHandler(partitionSearchInput, partitionItems) {
        if (partitionSearchInput) {
            partitionSearchInput.addEventListener('input', function() {
                var filter = this.value.toLowerCase();
                partitionItems.forEach(function(item) {
                    var label = item.querySelector('label').textContent.toLowerCase();
                    item.style.display = label.includes(filter) ? 'flex' : 'none';
                });
            });
        }
    }
    
    function setupNodeCheckboxHandlers(checkboxes, selectedNodes, updateCallback, highlightCallback) {
        checkboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedNodes.add(this.value);
                } else {
                    selectedNodes.delete(this.value);
                }
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    function setupPartitionCheckboxHandlers(partitionCheckboxes, selectedPartitions, updateCallback, highlightCallback) {
        partitionCheckboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedPartitions.add(this.value);
                } else {
                    selectedPartitions.delete(this.value);
                }
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    function setupItemClickHandlers(checkboxItems) {
        checkboxItems.forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.tagName !== 'INPUT') {
                    var checkbox = this.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }
    
    function setupPartitionItemClickHandlers(partitionItems) {
        partitionItems.forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
                    var checkbox = this.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }
    
    function setupEdgeDirectionHandlers(edgeDirectionRadios, selectedNodes, highlightCallback) {
        edgeDirectionRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                if (selectedNodes.size > 0) highlightCallback();
            });
        });
    }
    
    function setupFilterModeHandlers(filterModeRadios, selectedNodes, selectedPartitions, updateFilterModeCallback, highlightCallback) {
        filterModeRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                updateFilterModeCallback();
                if (selectedNodes.size > 0 || selectedPartitions.size > 0) highlightCallback();
            });
        });
    }
    
    function setupClearButtonHandler(btnClear, selectedNodes, selectedPartitions, checkboxes, partitionCheckboxes, updateCallback, searchResults, searchInput, checkboxItems, handleEdgeVisibilityCallback) {
        btnClear.addEventListener('click', function() {
            selectedNodes.clear();
            selectedPartitions.clear();
            checkboxes.forEach(function(cb) { cb.checked = false; });
            partitionCheckboxes.forEach(function(cb) { cb.checked = false; });
            
            // Uncheck special selection checkboxes
            var selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
            var selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
            if (selectLeafNodesCheckbox) selectLeafNodesCheckbox.checked = false;
            if (selectSourceNodesCheckbox) selectSourceNodesCheckbox.checked = false;
            
            updateCallback();
            network.selectNodes([]);
            searchResults.textContent = '';
            searchInput.value = '';
            checkboxItems.forEach(function(item) { item.style.display = 'flex'; });
            
            handleEdgeVisibilityCallback();
        });
    }
    
    function setupToggleButtonHandler(toggleBtn, searchContent) {
        toggleBtn.addEventListener('click', function() {
            if (searchContent.classList.contains('hidden')) {
                searchContent.classList.remove('hidden');
                toggleBtn.textContent = 'Hide';
            } else {
                searchContent.classList.add('hidden');
                toggleBtn.textContent = 'Show';
            }
        });
    }
    
    function setupSCCHandler(sccToggle, sccs, network) {
        if (sccToggle && typeof sccs !== 'undefined' && sccs.length > 0) {
            sccToggle.addEventListener('change', function() {
                GraphSCC.toggleSccs(network, sccs, sccToggle);
            });
        }
    }
    
    function setupRankingsToggle(rankingsToggleBtn, rankingsContent, rankingsHeader) {
        if (rankingsToggleBtn && rankingsContent && rankingsHeader) {
            rankingsToggleBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (rankingsContent.classList.contains('collapsed')) {
                    rankingsContent.classList.remove('collapsed');
                    rankingsToggleBtn.textContent = 'Hide';
                } else {
                    rankingsContent.classList.add('collapsed');
                    rankingsToggleBtn.textContent = 'Show';
                }
            });
            
            rankingsHeader.addEventListener('click', function(e) {
                if (e.target !== rankingsToggleBtn) {
                    rankingsToggleBtn.click();
                }
            });
        }
    }
    
    
    function initializePartitionStats() {
        // Display partition stats on load
        function updateStatsDisplay(stats) {
            var statsDiv = document.getElementById('partition-stats');
            if (statsDiv && stats) {
                statsDiv.innerHTML = 
                    '<div style="margin-bottom: 2px;"><strong>Initial partitions:</strong> ' + stats.initial_count + '</div>' +
                    '<div style="margin-bottom: 2px;"><strong>After merging:</strong> ' + stats.merged_count + '</div>' +
                    '<div style="font-style: italic;">Strategy: ' + stats.strategy + '</div>';
            }
        }
        
        // Set initial stats
        if (window.graphData && window.graphData.stats) {
            updateStatsDisplay(window.graphData.stats);
        }
    }
    
    return {
        setupSearchHandlers: setupSearchHandlers,
        setupPartitionSearchHandler: setupPartitionSearchHandler,
        setupNodeCheckboxHandlers: setupNodeCheckboxHandlers,
        setupPartitionCheckboxHandlers: setupPartitionCheckboxHandlers,
        setupItemClickHandlers: setupItemClickHandlers,
        setupPartitionItemClickHandlers: setupPartitionItemClickHandlers,
        setupEdgeDirectionHandlers: setupEdgeDirectionHandlers,
        setupFilterModeHandlers: setupFilterModeHandlers,
        setupClearButtonHandler: setupClearButtonHandler,
        setupToggleButtonHandler: setupToggleButtonHandler,
        setupSCCHandler: setupSCCHandler,
        setupRankingsToggle: setupRankingsToggle,
        initializePartitionStats: initializePartitionStats
    };
})();
