#include "btree.hpp"
#include <algorithm>
#include <cstring>

namespace toydb {

BTree::BTree(BufferPool* buffer_pool, PageManager* page_manager)
    : buffer_pool_(buffer_pool), 
      page_manager_(page_manager),
      root_page_id_(INVALID_PAGE_ID) {}

PageID BTree::CreateTree() {
    // Allocate root node (starts as a leaf)
    root_page_id_ = AllocateNode(NodeType::LEAF);
    return root_page_id_;
}

void BTree::OpenTree(PageID root_id) {
    root_page_id_ = root_id;
}

PageID BTree::AllocateNode(NodeType type) {
    PageID page_id = page_manager_->AllocatePage();
    
    BTreeNode node;
    node.type = type;
    node.num_keys = 0;
    node.next_leaf = INVALID_PAGE_ID;
    
    SaveNode(page_id, node);
    return page_id;
}

BTree::BTreeNode BTree::LoadNode(PageID page_id) {
    auto page = buffer_pool_->FetchPage(page_id);
    if (!page) {
        throw std::runtime_error("Failed to load B-Tree node");
    }
    
    BTreeNode node;
    
    // Read node header from page
    size_t offset = sizeof(Page::Header);
    
    // Read type, num_keys, next_leaf
    uint8_t type_val;
    page->ReadData(offset, reinterpret_cast<char*>(&type_val), sizeof(uint8_t));
    node.type = static_cast<NodeType>(type_val);
    offset += sizeof(uint8_t);
    
    page->ReadData(offset, reinterpret_cast<char*>(&node.num_keys), sizeof(uint16_t));
    offset += sizeof(uint16_t);
    
    page->ReadData(offset, reinterpret_cast<char*>(&node.next_leaf), sizeof(PageID));
    offset += sizeof(PageID);
    
    // Read keys
    for (uint16_t i = 0; i < node.num_keys; ++i) {
        // Read key length
        uint16_t key_len;
        page->ReadData(offset, reinterpret_cast<char*>(&key_len), sizeof(uint16_t));
        offset += sizeof(uint16_t);
        
        // Read key data
        char key_buf[256];
        page->ReadData(offset, key_buf, key_len);
        node.keys.emplace_back(key_buf, key_len);
        offset += key_len;
    }
    
    if (node.type == NodeType::LEAF) {
        // Read values for leaf nodes
        for (uint16_t i = 0; i < node.num_keys; ++i) {
            uint16_t val_len;
            page->ReadData(offset, reinterpret_cast<char*>(&val_len), sizeof(uint16_t));
            offset += sizeof(uint16_t);
            
            char val_buf[256];
            page->ReadData(offset, val_buf, val_len);
            node.values.emplace_back(val_buf, val_len);
            offset += val_len;
        }
    } else {
        // Read child pointers for internal nodes
        // Internal nodes have num_keys + 1 children
        for (uint16_t i = 0; i <= node.num_keys; ++i) {
            PageID child_id;
            page->ReadData(offset, reinterpret_cast<char*>(&child_id), sizeof(PageID));
            node.children.push_back(child_id);
            offset += sizeof(PageID);
        }
    }
    
    return node;
}

void BTree::SaveNode(PageID page_id, const BTreeNode& node) {
    auto page = buffer_pool_->FetchPage(page_id);
    if (!page) {
        throw std::runtime_error("Failed to save B-Tree node");
    }
    
    size_t offset = sizeof(Page::Header);
    
    // Write node header
    uint8_t type_val = static_cast<uint8_t>(node.type);
    page->WriteData(offset, reinterpret_cast<const char*>(&type_val), sizeof(uint8_t));
    offset += sizeof(uint8_t);
    
    page->WriteData(offset, reinterpret_cast<const char*>(&node.num_keys), sizeof(uint16_t));
    offset += sizeof(uint16_t);
    
    page->WriteData(offset, reinterpret_cast<const char*>(&node.next_leaf), sizeof(PageID));
    offset += sizeof(PageID);
    
    // Write keys
    for (const auto& key : node.keys) {
        uint16_t key_len = key.size();
        page->WriteData(offset, reinterpret_cast<const char*>(&key_len), sizeof(uint16_t));
        offset += sizeof(uint16_t);
        
        page->WriteData(offset, key.c_str(), key_len);
        offset += key_len;
    }
    
    if (node.type == NodeType::LEAF) {
        // Write values for leaf nodes
        for (const auto& value : node.values) {
            uint16_t val_len = value.size();
            page->WriteData(offset, reinterpret_cast<const char*>(&val_len), sizeof(uint16_t));
            offset += sizeof(uint16_t);
            
            page->WriteData(offset, value.c_str(), val_len);
            offset += val_len;
        }
    } else {
        // Write child pointers for internal nodes
        for (PageID child_id : node.children) {
            page->WriteData(offset, reinterpret_cast<const char*>(&child_id), sizeof(PageID));
            offset += sizeof(PageID);
        }
    }
    
    buffer_pool_->MarkDirty(page_id);
}

int BTree::SearchInNode(const BTreeNode& node, const std::string& key) {
    // Binary search for key position
    int left = 0, right = node.num_keys - 1;
    int result = node.num_keys;
    
    while (left <= right) {
        int mid = left + (right - left) / 2;
        
        if (node.keys[mid] < key) {
            left = mid + 1;
        } else {
            result = mid;
            right = mid - 1;
        }
    }
    
    return result;
}

PageID BTree::FindLeaf(const std::string& key) {
    if (root_page_id_ == INVALID_PAGE_ID) {
        return INVALID_PAGE_ID;
    }
    
    PageID current = root_page_id_;
    
    while (true) {
        BTreeNode node = LoadNode(current);
        
        if (node.type == NodeType::LEAF) {
            return current;
        }
        
        // Internal node - find the child to descend into
        int pos = SearchInNode(node, key);
        current = node.children[pos];
    }
}

std::optional<std::string> BTree::Search(const std::string& key) {
    PageID leaf_id = FindLeaf(key);
    if (leaf_id == INVALID_PAGE_ID) {
        return std::nullopt;
    }
    
    BTreeNode leaf = LoadNode(leaf_id);
    
    // Search for key in leaf
    for (size_t i = 0; i < leaf.num_keys; ++i) {
        if (leaf.keys[i] == key) {
            return leaf.values[i];
        }
    }
    
    return std::nullopt;
}

bool BTree::Insert(const std::string& key, const std::string& value) {
    if (root_page_id_ == INVALID_PAGE_ID) {
        CreateTree();
    }
    
    BTreeNode root = LoadNode(root_page_id_);
    
    // If root is full, split it
    if (root.num_keys >= ORDER - 1) {
        PageID new_root_id = AllocateNode(NodeType::INTERNAL);
        BTreeNode new_root;
        new_root.type = NodeType::INTERNAL;
        new_root.num_keys = 0;
        new_root.children.push_back(root_page_id_);
        
        SaveNode(new_root_id, new_root);
        
        SplitChild(new_root_id, 0, root_page_id_);
        
        root_page_id_ = new_root_id;
    }
    
    return InsertNonFull(root_page_id_, key, value);
}

bool BTree::InsertNonFull(PageID page_id, const std::string& key, const std::string& value) {
    BTreeNode node = LoadNode(page_id);
    
    if (node.type == NodeType::LEAF) {
        // Find insertion position
        int pos = SearchInNode(node, key);
        
        // Check if key already exists
        if (pos < node.num_keys && node.keys[pos] == key) {
            // Update existing value
            node.values[pos] = value;
            SaveNode(page_id, node);
            return true;
        }
        
        // Insert new key-value pair
        node.keys.insert(node.keys.begin() + pos, key);
        node.values.insert(node.values.begin() + pos, value);
        node.num_keys++;
        
        SaveNode(page_id, node);
        return true;
    } else {
        // Internal node - find child to descend into
        int pos = SearchInNode(node, key);
        PageID child_id = node.children[pos];
        
        BTreeNode child = LoadNode(child_id);
        
        // If child is full, split it first
        if (child.num_keys >= ORDER - 1) {
            SplitChild(page_id, pos, child_id);
            
            // After split, determine which child to insert into
            node = LoadNode(page_id);
            if (key > node.keys[pos]) {
                pos++;
            }
            child_id = node.children[pos];
        }
        
        return InsertNonFull(child_id, key, value);
    }
}

void BTree::SplitChild(PageID parent_id, int child_index, PageID child_id) {
    BTreeNode parent = LoadNode(parent_id);
    BTreeNode child = LoadNode(child_id);
    
    // Create new sibling node
    PageID sibling_id = AllocateNode(child.type);
    BTreeNode sibling;
    sibling.type = child.type;
    
    int mid = ORDER / 2;
    
    // Move half of the keys to the sibling
    sibling.keys.assign(child.keys.begin() + mid, child.keys.end());
    sibling.num_keys = child.num_keys - mid;
    
    if (child.type == NodeType::LEAF) {
        // For leaf nodes, copy values and link siblings
        sibling.values.assign(child.values.begin() + mid, child.values.end());
        sibling.next_leaf = child.next_leaf;
        child.next_leaf = sibling_id;
        
        // Truncate child
        child.keys.resize(mid);
        child.values.resize(mid);
        child.num_keys = mid;
    } else {
        // For internal nodes, move children pointers
        sibling.children.assign(child.children.begin() + mid, child.children.end());
        
        child.keys.resize(mid);
        child.children.resize(mid + 1);
        child.num_keys = mid;
    }
    
    // Promote middle key to parent
    std::string promoted_key = child.type == NodeType::LEAF ? sibling.keys[0] : child.keys[mid - 1];
    
    parent.keys.insert(parent.keys.begin() + child_index, promoted_key);
    parent.children.insert(parent.children.begin() + child_index + 1, sibling_id);
    parent.num_keys++;
    
    // Save all modified nodes
    SaveNode(child_id, child);
    SaveNode(sibling_id, sibling);
    SaveNode(parent_id, parent);
}

bool BTree::Delete(const std::string& key) {
    // TODO: Implement delete with node merging
    // For Phase 2, we'll skip delete to keep it simple
    return false;
}

std::vector<std::pair<std::string, std::string>> BTree::RangeScan(
    const std::string& start_key, 
    const std::string& end_key
) {
    std::vector<std::pair<std::string, std::string>> results;
    
    if (root_page_id_ == INVALID_PAGE_ID) {
        return results;
    }
    
    // Find the starting leaf node
    PageID leaf_id = FindLeaf(start_key);
    
    while (leaf_id != INVALID_PAGE_ID) {
        BTreeNode leaf = LoadNode(leaf_id);
        
        for (size_t i = 0; i < leaf.num_keys; ++i) {
            if (leaf.keys[i] >= start_key && leaf.keys[i] <= end_key) {
                results.emplace_back(leaf.keys[i], leaf.values[i]);
            } else if (leaf.keys[i] > end_key) {
                return results;  // Done
            }
        }
        
        // Move to next leaf
        leaf_id = leaf.next_leaf;
    }
    
    return results;
}

} // namespace toydb
