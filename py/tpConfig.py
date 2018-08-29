
import os
import json


class TpConfig:
    """
    設定を扱うクラス
    """

    def __init__(self, host=None, slot=None, comm=None, setting_file=None):
        """
        コンストラクタ
        """

        # 設定の読み込み
        settings = self.__read_settings(setting_file)

        if (host is not None and slot is not None and comm is not None):

            # hostとslotとcommの指定がある場合、その設定のみ保持
            for setting in settings:
                if (setting['host'] == host and setting['slot'] == slot and setting['comm'] == comm):
                    self.setting = setting
                    break

            if hasattr(self, 'setting') == False:
                # 見つからない場合
                raise ValueError(
                    "There is no setting: host:" + host + " slot:" + slot + " comm:" + comm)

        else:
            # hostとslotとcommの指定が無い場合、すべての設定を保持
            self.settings = settings

    def __read_settings(self, setting_file):
        """
        設定ファイルを読み込みます。
        """

        if (setting_file is None or setting_file == ''):
            # Def
            setting_file = os.path.abspath(os.path.join(
                os.path.dirname(__file__), os.pardir)) + '/config/config.json'

        # 設定ファイルが存チェック
        if os.path.exists(setting_file) == False:
            raise FileNotFoundError("Not Found: " + setting_file)

        # 設定の読み込み
        f = open(setting_file, 'r')
        return json.load(f)

    def get_setting(self, host=None, slot=None, comm=None):
        """
        設定を取得します。
        """
        _setting = None
        if (host is None and slot is None and comm is None):
            _setting = self.setting
        else:
            for setting in self.settings:
                if (setting['host'] == host and setting['slot'] == slot and setting['comm'] == comm):
                    _setting = setting
                    break

        return _setting

    def get_settings(self):
        """
        すべての設定を取得します。
        """
        return self.settings
