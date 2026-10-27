package com.easymeals.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.*
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.ui.screens.*
import com.easymeals.app.ui.theme.EasyMealsTheme

enum class AppTab(val title: String, val icon: ImageVector) {
    TODAY("Hôm nay", Icons.Default.DinnerDining),
    PANTRY("Tủ lạnh", Icons.Default.Kitchen),
    SHOPPING("Đi chợ", Icons.Default.ShoppingCart),
    RECIPES("Công thức", Icons.Default.MenuBook),
    SETTINGS("Cài đặt", Icons.Default.Settings)
}

class MainActivity : ComponentActivity() {

    private lateinit var repository: AppRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        repository = AppRepository(applicationContext)

        // F2: tạo kênh thông báo và khôi phục lịch nhắc sau khi máy khởi động lại/mở app.
        com.easymeals.app.data.notifications.ReminderScheduler.applySetting(this)

        setContent {
            val themeMode by repository.themeMode.collectAsState()
            val palette by repository.palette.collectAsState()
            EasyMealsTheme(themeMode = themeMode, palette = palette) {
                MainContent(repository = repository)
            }
        }
    }
}

@Composable
fun MainContent(repository: AppRepository) {
    var selectedTab by remember { mutableStateOf(AppTab.TODAY) }
    val undoMessage by repository.undoMessage.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    BackHandler(enabled = selectedTab != AppTab.TODAY) {
        selectedTab = AppTab.TODAY
    }

    LaunchedEffect(undoMessage) {
        val msg = undoMessage
        if (msg != null) {
            val result = snackbarHostState.showSnackbar(
                message = msg,
                actionLabel = "Hoàn tác",
                duration = SnackbarDuration.Short
            )
            if (result == SnackbarResult.ActionPerformed) {
                repository.undoLastEatMeal()
            }
            repository.clearUndoMessage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surfaceContainer,
                tonalElevation = 8.dp
            ) {
                AppTab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = selectedTab == tab,
                        onClick = { selectedTab = tab },
                        icon = { Icon(tab.icon, contentDescription = tab.title) },
                        label = { Text(tab.title) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTab) {
                AppTab.TODAY -> TodayScreen(repository)
                AppTab.PANTRY -> PantryScreen(repository)
                AppTab.SHOPPING -> ShoppingScreen(repository)
                AppTab.RECIPES -> RecipesScreen(repository)
                AppTab.SETTINGS -> SettingsScreen(repository)
            }
        }
    }
}
