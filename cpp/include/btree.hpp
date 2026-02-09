#pragma once

#include "page.hpp"
#include "page_manager.hpp"
#include "buffer_pool.hpp"
#include <string>
#include <vector>
#include <optional>
#include <memory>

namespace toydb {

/**
 * BTree - B+Tree index for key-value storage
 * 
 * Properties:
 * - Keys are sorted
 * - All values stored in leaf nodes
 * - Internal nodes only store keys for navigation
 * - Leaf nodes are linked for range scans
 * 
 * B-Tree order: Max number of children per node
 * For simplicity, we'll use a small order to fit in pages
 */
class BTree {
public:
    // B-Tree configuration
    static constexpr size_t ORDER = 16;  // Max 16 keys per node
    static constexpr size_t MIN_KEYS = ORDER / 2;  // Min keys (for balancing)
    
    explicit BTree(BufferPool* buffer_pool, PageManager* page_manager);
    ~BTree() = default;
    
    // Create a new empty B-Tree (returns root page ID)
    PageID CreateTree();
    
    // Open existing B-Tree from root page ID
    void OpenTree(PageID root_id);
    
    // Insert key-value pair
    bool Insert(const std::string& key, const std::string& value);
    
    // Search for a key
    std::optional<std::string> Search(const std::string& key);
    
    // Delete a key
    bool Delete(const std::string& key);
    
    // Range scan: get all keys between start and end (inclusive)
    std::vector<std::pair<std::string, std::string>> RangeScan(
        const std::string& start_key, 
        const std::string& end_key
    );
    
    // Get root page ID
    PageID GetRootID() const { return root_page_id_; }

private:
    BufferPool* buffer_pool_;
    PageManager* page_manager_;
    PageID root_page_id_;
    
    // Node types
    enum class NodeType : uint8_t {
        INTERNAL = 0,  // Internal (non-leaf) node
        LEAF = 1       // Leaf node
    };
    
    // B-Tree node structure (stored in pages)
    struct BTreeNode {
        NodeType type;
        uint16_t num_keys;
        PageID next_leaf;  // For leaf nodes: pointer to next leaf (for range scans)
        
        // Keys and values (for leaf nodes) or child pointers (for internal nodes)
        std::vector<std::string> keys;
        std::vector<std::string> values;      // Only for leaf nodes
        std::vector<PageID> children;          // Only for internal nodes
        
        BTreeNode() : type(NodeType::LEAF), num_keys(0), next_leaf(INVALID_PAGE_ID) {}
    };
    
    // Load node from page
    BTreeNode LoadNode(PageID page_id);
    
    // Save node to page
    void SaveNode(PageID page_id, const BTreeNode& node);
    
    // Allocate new node
    PageID AllocateNode(NodeType type);
    
    // Search within a node (returns child index or -1)
    int SearchInNode(const BTreeNode& node, const std::string& key);
    
    // Insert into a non-full node
    bool InsertNonFull(PageID page_id, const std::string& key, const std::string& value);
    
    // Split a full child node
    void SplitChild(PageID parent_id, int child_index, PageID child_id);
    
    // Find leaf node for a given key
    PageID FindLeaf(const std::string& key);
};

} // namespace toydb
