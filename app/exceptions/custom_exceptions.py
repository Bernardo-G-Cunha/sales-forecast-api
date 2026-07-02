class StoreNotFoundError(Exception):
    def __init__(self, store_id: int):
        self.store_id = store_id
        super().__init__(f"Store {store_id} not found.")