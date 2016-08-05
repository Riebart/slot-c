myApp.controller('usernameSectionCtrl', ['$scope', '$rootScope', '$resource', '$timeout', function ($scope, $rootScope, $resource, $timeout) {
    $scope.userName = 'Enter UserName';
    $scope.seconds_until_refresh = 0;

    $scope.versionResource = $resource("version.json");
    $scope.check_version = function () {
        $scope.versionResource.get(null, function (version) {
            if ($scope.version == null) {
                $scope.version = { 'hash': version.hash };
            }
            else if ($scope.version.hash != version.hash) {
                console.log('Version mismatch');
                $scope.seconds_until_refresh = 3600;
                $scope.$emit('version_mismatch');
            }
        });
    };

    $scope.version = null;
    $scope.check_version();

    $scope.$on('version_mismatch', function () {
        var poll = function () {
            $timeout(function () {
                if ($scope.seconds_until_refresh == 1) {
                    location.reload();
                }
                else {
                    $scope.seconds_until_refresh -= 1;
                    poll();
                }
            }, 1000);
        };
        poll();
    });

    // Every 60 seconds, check on the webapp version file.
    $scope.$on('update_check', function () {
        var poll = function () {
            $timeout(function () {
                $scope.check_version();
                if ($scope.seconds_until_refresh == 0) {
                    poll();
                }
            }, 300000);
        };
        poll();
    });

    $scope.toggleChatting = function () {
        if ($rootScope.chatting) {
            $scope.logoff();
        }
        else {
            $scope.login();
        }
    };

    $scope.login = function () {
        $rootScope.chatting = true;
        $rootScope.userName = document.getElementById('name-input').value;
        localStorage.userName = $rootScope.userName;
        $rootScope.channel = DEFAULT_CHANNEL_NAME;
        $rootScope.$emit('chatting');
        //document.getElementById('name-input').disabled = true;
        document.getElementById('chat-toggle').value = "Stop Chatting";
    };

    $scope.logoff = function () {
        document.getElementById('chat-toggle').value = "Start Chatting";
        //document.getElementById('name-input').disabled = false;
        $rootScope.chatting = false;
        localStorage.removeItem('userName');
        $rootScope.$emit('not chatting');
    };

    if (localStorage.getItem('userName') !== null) {
        document.getElementById('name-input').value = localStorage.userName;
        $scope.toggleChatting();
    }

    $scope.$emit('update_check');
}]);
